#!/usr/bin/env python3
"""Persistent local Age of Empires III engine, with detach/reconnect to preserve the live session.

Quickshell starts the default client. Closing its stdin detaches only the client.
The Java game remains alive and suspended, until `python3 bridge.py stop` or logout.
The original J2ME RMS records remain stored in the engine's existing state directory.
"""
from pathlib import Path
import fcntl
import json
import os
import selectors
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
STATE = Path.home() / '.local/state/impasto-aoe3'
STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
SOCKET = STATE / 'engine.sock'
CONTROL = STATE / 'engine-control.sock'
LOG = STATE / 'runtime.log'
FRAMES = Path(os.environ.get('XDG_RUNTIME_DIR') or '/tmp') / ('impasto-aoe3-' + str(os.getuid()))


def message(kind, **kwargs):
    return (json.dumps({'type': kind, **kwargs}) + '\n').encode()


def connect(timeout=0.4):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(str(SOCKET))
        sock.settimeout(None)
        return sock
    except OSError:
        sock.close()
        return None


def java_input(java, text):
    if java.poll() is None:
        try:
            java.stdin.write((text + '\n').encode())
            java.stdin.flush()
        except (OSError, BrokenPipeError):
            pass


def server():
    lock_file = (STATE / 'engine.lock').open('a+')
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 0

    java = shutil.which('java')
    if not java:
        LOG.open('a').write('Java 17+ required for Age of Empires III\n')
        return 1
    FRAMES.mkdir(mode=0o700, parents=True, exist_ok=True)

    # Only the lock owner may unlink the socket, so concurrent open attempts
    # cannot delete each other's endpoint.
    SOCKET.unlink(missing_ok=True)
    CONTROL.unlink(missing_ok=True)
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(SOCKET))
    os.chmod(SOCKET, 0o600)
    listener.listen(2)
    listener.setblocking(False)
    ctl = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    ctl.bind(str(CONTROL))
    os.chmod(CONTROL, 0o600)
    ctl.listen(2)
    ctl.setblocking(False)

    log = LOG.open('a', buffering=1)
    proc = subprocess.Popen(
        [java, '-Xmx256m', '-Djava.awt.headless=true', '-cp',
         os.pathsep.join((str(ROOT / 'midp-runtime.jar'), str(ROOT / 'Age-of-Empires-III.jar'))),
         'Bridge', str(STATE), str(FRAMES)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, bufsize=0)
    os.set_blocking(proc.stdout.fileno(), False)
    sel = selectors.DefaultSelector()
    sel.register(listener, selectors.EVENT_READ, 'listener')
    sel.register(ctl, selectors.EVENT_READ, 'control')
    sel.register(proc.stdout, selectors.EVENT_READ, 'java')
    client = None
    input_buffer = b''
    output_buffer = b''
    last_frame = None
    latest_seq = 0
    paused = False
    stopping = False

    def disconnect():
        nonlocal client, input_buffer, paused
        if client is not None:
            try: sel.unregister(client)
            except (OSError, KeyError): pass
            try: client.close()
            except OSError: pass
            client = None
        input_buffer = b''
        # Pause the original game logic, rather than merely hiding its image.
        if not stopping and not paused:
            java_input(proc, 'suspend')
            java_input(proc, 'save')
            paused = True

    try:
        while proc.poll() is None and not stopping:
            for key, _ in sel.select(0.15):
                if key.data == 'control':
                    control_conn, _ = ctl.accept()
                    try:
                        control_conn.settimeout(0.5)
                        payload = control_conn.recv(128)
                        if payload.strip() == b'stop':
                            stopping = True
                            control_conn.sendall(b'STOPPING\n')
                    except OSError:
                        pass
                    finally:
                        control_conn.close()
                elif key.data == 'listener':
                    conn, _ = listener.accept()
                    conn.setblocking(False)
                    if client is not None:
                        try: conn.sendall(message('error', message='Age of Empires III already has an open panel'))
                        except OSError: pass
                        conn.close()
                        continue
                    client = conn
                    input_buffer = b''
                    sel.register(client, selectors.EVENT_READ, 'client')
                    if paused:
                        java_input(proc, 'resume')
                        paused = False
                    if last_frame is not None and Path(last_frame).is_file():
                        try: client.sendall(message('frame', seq=latest_seq, path=last_frame))
                        except OSError: disconnect()
                elif key.data == 'java':
                    try: data = os.read(proc.stdout.fileno(), 65536)
                    except BlockingIOError: data = b''
                    if data:
                        output_buffer += data
                        while b'\n' in output_buffer:
                            line, output_buffer = output_buffer.split(b'\n', 1)
                            if line.startswith(b'FRAME '):
                                try:
                                    _, seq, framepath = line.decode(errors='replace').split(' ', 2)
                                    latest_seq, last_frame = int(seq), framepath
                                    if client is not None:
                                        try: client.sendall(message('frame', seq=latest_seq, path=last_frame))
                                        except (OSError, BlockingIOError): disconnect()
                                except (ValueError, UnicodeError):
                                    continue
                            elif line.startswith(b'SAVED '):
                                log.write(line.decode(errors='replace') + '\n')
                elif key.data == 'client':
                    try: data = client.recv(4096)
                    except (OSError, BlockingIOError): data = b''
                    if not data:
                        disconnect()
                    else:
                        input_buffer += data
                        while b'\n' in input_buffer:
                            line, input_buffer = input_buffer.split(b'\n', 1)
                            cmd = line.decode(errors='replace').strip()
                            if cmd == 'detach':
                                disconnect()
                                break
                            if cmd == 'stop':
                                stopping = True
                                break
                            if cmd.startswith(('down ', 'up ', 'tap ')):
                                java_input(proc, cmd)
            # Don't let a Java process exit silently without notifying active panel.
        if client is not None:
            try: client.sendall(message('error', message='Engine stopped'))
            except OSError: pass
    finally:
        disconnect()
        java_input(proc, 'quit')
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try: proc.wait(timeout=2)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait()
        sel.close()
        listener.close()
        ctl.close()
        SOCKET.unlink(missing_ok=True)
        CONTROL.unlink(missing_ok=True)
        log.close()
        lock_file.close()
    return 0


def client():
    sock = connect()
    if sock is None:
        with LOG.open('ab') as logfile:
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--server'],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=logfile, start_new_session=True, close_fds=True)
        for _ in range(100):
            sock = connect()
            if sock is not None:
                break
            time.sleep(0.05)
    if sock is None:
        print(json.dumps({'type': 'error', 'message': f'Cannot start Age of Empires III background engine. See {LOG}'}), flush=True)
        return 1

    sel = selectors.DefaultSelector()
    sel.register(sock, selectors.EVENT_READ, 'server')
    sel.register(sys.stdin.buffer, selectors.EVENT_READ, 'qml')
    buffer = b''
    try:
        while True:
            for key, _ in sel.select(0.5):
                if key.data == 'qml':
                    data = os.read(sys.stdin.fileno(), 4096)
                    if not data:
                        return 0
                    try: sock.sendall(data)
                    except OSError: return 1
                    if b'detach\n' in data:
                        return 0
                else:
                    data = sock.recv(65536)
                    if not data:
                        return 0
                    buffer += data
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        print(line.decode(errors='replace'), flush=True)
    finally:
        sel.close()
        sock.close()


def stop():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect(str(CONTROL))
        sock.sendall(b'stop\n')
        reply = sock.recv(128)
    except OSError:
        print('Age of Empires III session is not running (or cannot be contacted).')
        return 1
    finally:
        sock.close()
    if reply != b'STOPPING\n':
        print('Background service did not confirm shutdown.')
        return 1
    print('Engine shutdown acknowledged. The game will attempt native RMS saving.')
    return 0


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        sys.exit(server())
    if len(sys.argv) > 1 and sys.argv[1] == 'stop':
        sys.exit(stop())
    sys.exit(client())
