#!/usr/bin/env python3
"""Local FIFO/frame-file bridge for the original Diamond Rush engine."""
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import os
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent


def paths(state, runtime=None):
    state = state.expanduser().resolve()
    parent = Path(os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir())
    runtime = runtime or parent/("impasto-diamondrush-"+str(os.getuid())+"-"+hashlib.sha256(str(state).encode()).hexdigest()[:12])
    if runtime.is_symlink():
        raise RuntimeError("Runtime directory must not be a symbolic link")
    runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    if runtime.stat().st_uid != os.getuid():
        raise RuntimeError("Runtime directory has a different owner")
    runtime.chmod(0o700)
    state.mkdir(parents=True, exist_ok=True)
    return state, runtime


def atomic_json(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, separators=(",", ":")))
    temp.replace(path)


def write_command(runtime, line):
    fd = os.open(runtime/"commands.fifo", os.O_WRONLY | os.O_NONBLOCK)
    try:
        os.write(fd, (line+"\n").encode())
    finally:
        os.close(fd)


class Server:
    def __init__(self, state, runtime, mute=False):
        self.state, self.runtime, self.mute = state, runtime, mute
        self.selector = selectors.DefaultSelector()
        self.java = None
        self.buffer = b""
        self.command_buffer = b""
        self.running = True
        self.had_clients = False
        self.idle_since = time.monotonic()
        self.report = {"frame": None, "saved": 0, "paused": False, "restored": 0, "error": "", "starting": 0}
        self.log = (state/"runtime.log").open("a", buffering=1)

    def publish(self):
        atomic_json(self.runtime/"latest.json", self.report)

    def write(self, line):
        if line in {"pause", "save"}:
            self.report["saved"] = 0
        if self.java and self.java.poll() is None:
            try:
                self.java.stdin.write((line+"\n").encode())
                self.java.stdin.flush()
            except BrokenPipeError:
                pass

    def launch(self):
        java = shutil.which("java")
        if not java:
            self.report["error"] = "Java 17 or newer is required. Install Java and reopen the game."
            self.publish()
            return
        self.java = subprocess.Popen([java,"-Xms32m","-Xmx256m","-Djava.awt.headless=true",
            "-Ddiamondrush.mute="+str(self.mute).lower(),"-cp",
            str(ROOT/"midp-runtime.jar")+os.pathsep+str(ROOT/"DiamondRush-runtime.jar"),
            "Bridge",str(self.state),str(self.runtime)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log)
        os.set_blocking(self.java.stdout.fileno(), False)
        self.selector.register(self.java.stdout, selectors.EVENT_READ, "java")
        self.buffer = b""

    def stop_java(self):
        if not self.java:
            return
        self.write("quit")
        try:
            self.java.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.java.terminate()
            try:
                self.java.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.java.kill()
                self.java.wait()
        try:
            self.selector.unregister(self.java.stdout)
        except KeyError:
            pass
        self.java.stdout.close()
        self.java.stdin.close()
        self.java = None

    def accept_command(self, line):
        if line == "stop":
            self.running = False
        elif line == "menu":
            self.stop_java()
            snapshot = self.state/"resume.bin.gz"
            if snapshot.exists():
                snapshot.replace(self.state/"resume-before-menu.bin.gz")
            self.report.update(frame=None, saved=0, error="", paused=False, starting=self.report["starting"]+1)
            self.publish()
            self.launch()
        elif line in {"pause","resume","save"}:
            self.write(line)
        else:
            parts = line.split()
            if len(parts)==2 and parts[0] in {"down","up","tap"}:
                try:
                    code = int(parts[1])
                except ValueError:
                    return
                if code in {-7,-6,-5,-4,-3,-2,-1,23,35,42,*range(48,58)}:
                    self.write(line)

    def accept_report(self, line):
        kind, _, rest = line.partition(" ")
        if kind=="FRAME":
            seq, _, rest = rest.partition(" ")
            path, world, stage, gems, mode, x, y = rest.rsplit(" ",6)
            self.report["frame"]={"type":"frame","seq":int(seq),"path":path,"world":int(world),"stage":int(stage),"gems":int(gems),"mode":int(mode),"x":int(x),"y":int(y)}
        elif kind=="SAVED":
            self.report["saved"]=int(rest)
        elif kind=="PAUSED":
            self.report["paused"]=rest=="1"
        elif kind=="RESTORED":
            self.report["restored"]=time.time_ns()
        elif kind=="ERROR":
            self.report["error"]=rest
        self.publish()

    def live_clients(self):
        count=0
        for marker in self.runtime.glob("client-*.json"):
            try:
                pid=int(marker.name.split("-")[1].split(".")[0])
                os.kill(pid,0)
                count+=1
            except (ValueError,ProcessLookupError):
                marker.unlink(missing_ok=True)
        return count

    def run(self):
        lock=(self.runtime/"daemon.lock").open("w")
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            return
        fifo=self.runtime/"commands.fifo"
        if fifo.exists() and not stat.S_ISFIFO(fifo.stat().st_mode):
            raise RuntimeError("Invalid command FIFO")
        if not fifo.exists():
            os.mkfifo(fifo,0o600)
        fd=os.open(fifo,os.O_RDWR|os.O_NONBLOCK)
        self.selector.register(fd,selectors.EVENT_READ,"commands")
        atomic_json(self.runtime/"owner.json", {"state": str(self.state), "bridge": str(ROOT/"bridge.py"), "pid": os.getpid()})
        signal.signal(signal.SIGTERM,lambda *_:setattr(self,"running",False))
        signal.signal(signal.SIGINT,lambda *_:setattr(self,"running",False))
        self.publish()
        self.launch()
        try:
            while self.running:
                for key,_ in self.selector.select(timeout=.1):
                    if key.data=="commands":
                        self.command_buffer+=os.read(fd,8192)
                        if len(self.command_buffer)>16384:
                            self.command_buffer=b""
                        while b"\n" in self.command_buffer:
                            line,self.command_buffer=self.command_buffer.split(b"\n",1)
                            self.accept_command(line.decode("ascii","ignore").strip())
                    else:
                        chunk=os.read(key.fileobj.fileno(),65536)
                        if not chunk:
                            self.selector.unregister(key.fileobj)
                            self.report["error"]="The game runtime stopped. Reopen the game or check runtime.log."
                            self.publish()
                            continue
                        self.buffer+=chunk
                        while b"\n" in self.buffer:
                            line,self.buffer=self.buffer.split(b"\n",1)
                            try:
                                self.accept_report(line.decode("utf-8","replace"))
                            except (ValueError,TypeError) as error:
                                print("Invalid runtime report:",error,file=self.log)
                clients=self.live_clients()
                if clients and not self.had_clients:
                    self.write("resume")
                elif not clients and self.had_clients:
                    self.write("pause")
                    self.idle_since=time.monotonic()
                self.had_clients=bool(clients)
                if not clients and (self.report["saved"] or self.report["error"]) and time.monotonic()-self.idle_since>30:
                    break
        finally:
            self.stop_java()
            os.close(fd)
            (self.runtime/"ready").unlink(missing_ok=True)
            self.log.close()


def alive(runtime):
    try:
        with (runtime/"daemon.lock").open("a") as lock:
            try:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                return False
            except BlockingIOError:
                return True
    except OSError:
        return False


def client(state,runtime,mute):
    if not alive(runtime):
        with (state/"bridge.log").open("a") as log:
            args=[sys.executable,str(ROOT/"bridge.py"),"daemon","--state",str(state),"--runtime",str(runtime)]
            if mute:
                args.append("--mute")
            subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
        deadline=time.monotonic()+12
        while not alive(runtime) or not (runtime/"commands.fifo").exists():
            if time.monotonic()>deadline:
                raise RuntimeError("Game bridge did not start; see bridge.log")
            time.sleep(.05)
    marker=runtime/("client-"+str(os.getpid())+".json")
    marker.write_text(str(time.time()))
    selector=selectors.DefaultSelector()
    selector.register(sys.stdin,selectors.EVENT_READ)
    active=True
    def stop(*_):
        nonlocal active
        active=False
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    previous={}
    input_buffer=b""
    try:
        while active:
            for key,_ in selector.select(timeout=.025):
                data=os.read(key.fileobj.fileno(),4096)
                if not data:
                    return
                input_buffer+=data
                if len(input_buffer)>16384:
                    input_buffer=b""
                while b"\n" in input_buffer:
                    line,input_buffer=input_buffer.split(b"\n",1)
                    write_command(runtime,line.decode("ascii","ignore"))
            try:
                latest=json.loads((runtime/"latest.json").read_text())
            except (FileNotFoundError,ValueError):
                continue
            events=[]
            if latest.get("starting")!=previous.get("starting") and latest.get("starting"):
                events.append({"type":"starting","message":"Opening the original menu…"})
            frame=latest.get("frame")
            if frame and frame!=previous.get("frame"):
                events.append(frame)
            for field in ["saved","restored"]:
                if latest.get(field) and latest.get(field)!=previous.get(field):
                    events.append({"type":field})
            if latest.get("paused")!=previous.get("paused"):
                events.append({"type":"paused","paused":latest.get("paused",False)})
            if latest.get("error") and latest.get("error")!=previous.get("error"):
                events.append({"type":"error","message":latest["error"]})
            for event in events:
                print(json.dumps(event,separators=(",",":")),flush=True)
            previous=latest
            if not alive(runtime):
                return
    finally:
        marker.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=["client","daemon","stop"])
    parser.add_argument("--state",type=Path,required=True)
    parser.add_argument("--runtime",type=Path)
    parser.add_argument("--mute",action="store_true")
    args=parser.parse_args()
    try:
        state,runtime=paths(args.state,args.runtime)
        if args.mode=="daemon":
            Server(state,runtime,args.mute).run()
        elif args.mode=="stop":
            if alive(runtime):
                write_command(runtime,"stop")
        else:
            client(state,runtime,args.mute)
    except Exception as error:
        print(json.dumps({"type":"error","message":str(error)}),flush=True)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
