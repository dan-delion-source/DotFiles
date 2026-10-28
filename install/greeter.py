#!/usr/bin/env python3
"""Explicit, reversible system integration for the Yozora boot greeter."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib

REPO = Path(__file__).resolve().parents[1]
CODE = Path('/usr/local/share/yozora-greeter')
DATA = Path('/var/lib/yozora-greeter')
CONFIG = Path('/etc/greetd/config.toml')
COMMAND = str(CODE / 'session.sh')
SHARED = {
    'theme/Theme.qml', 'services/BatteryService.qml', 'bar/widgets/BatteryWidget.qml',
    'components/Avatar.qml', 'components/RingIndicator.qml', 'components/NotchFillet.qml',
    'lock/LockStyleHost.qml', 'lock/LockStyles.js', 'lock/LockSurface.qml', 'lock/LockClock.qml',
    'lock/LockAccount.qml', 'lock/LockIsland.qml', 'lock/LockPower.qml', 'lock/Padlock.qml',
    'lock/FaceRing.qml', 'lock/MainframeSurface.qml', 'lock/MainframeView.qml', 'lock/MainframeClock.qml',
    'lock/shaders/mainframe-crt.frag', 'lock/shaders/mainframe-crt.frag.qsb',
}


def current_command(config=CONFIG):
    return tomllib.loads(config.read_text())['default_session']['command']


def replace_command(contents, command):
    lines = contents.splitlines(keepends=True)
    active, found = False, False
    for index, line in enumerate(lines):
        if re.match(r'^\s*\[', line):
            active = bool(re.match(r'^\s*\[default_session\]\s*(?:#.*)?$', line.rstrip()))
        elif active and re.match(r'^\s*command\s*=', line):
            lines[index] = 'command = ' + json.dumps(command) + '\n'
            found = True
    if not found:
        raise ValueError('greetd config needs an existing default_session.command')
    result = ''.join(lines)
    if tomllib.loads(result)['default_session']['command'] != command:
        raise ValueError('Could not validate the new greetd command')
    return result


def stage_bundle(destination, uid, repo=REPO):
    account = pwd.getpwuid(uid)
    destination.mkdir(parents=True)
    for source in sorted((repo / 'greeter').rglob('*')):
        if source.is_symlink():
            raise ValueError('Greeter source must not contain symlinks')
        if source.is_file() and source.suffix in ('.qml', '.lua', '.sh', '.py'):
            relative = source.relative_to(repo / 'greeter')
            if '__pycache__' in relative.parts or 'tests' in relative.parts:
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    for name in SHARED:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo / 'config/quickshell' / name, target)
    shutil.copy2(repo / 'config/quickshell/scripts/greeter.py', destination / 'backend.py')
    (destination / 'config.json').write_text(json.dumps({'version': 1, 'uid': uid, 'user': account.pw_name}) + '\n')
    for path in destination.rglob('*'):
        path.chmod(0o755 if path.is_dir() or path.suffix == '.sh' else 0o644)
    subprocess.run(['/usr/lib/qt6/bin/qsb', '--glsl', '100 es,120,150', '--hlsl', '50', '--msl', '12',
                    '-o', str(destination / 'lock/shaders/mainframe-crt.frag.qsb'),
                    str(destination / 'lock/shaders/mainframe-crt.frag')], check=True, capture_output=True)


def inventory(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError('Greeter bundle contains a non-regular file: ' + str(path))
        if path.is_file():
            result[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def validate_bundle(bundle):
    """Render both designs offscreen, without authentication or a compositor."""
    with tempfile.TemporaryDirectory(prefix='yozora-greeter-check-') as temporary:
        root = Path(temporary)
        (root / 'runtime').mkdir(mode=0o700)
        env = dict(os.environ, HOME=temporary, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                   YOZORA_GREETER_PREVIEW='1', YOZORA_GREETER_DATA=str(root / 'data'),
                   XDG_RUNTIME_DIR=str(root / 'runtime'), XDG_CONFIG_HOME=str(root / 'config'),
                   XDG_STATE_HOME=str(root / 'state'), XDG_DATA_HOME=str(root / 'share'),
                   XDG_CACHE_HOME=str(root / 'cache'))
        for key in ('GREETD_SOCK', 'HYPRLAND_INSTANCE_SIGNATURE', 'WAYLAND_DISPLAY'):
            env.pop(key, None)
        harness = bundle / 'validate.qml'
        harness.write_text('''import QtQuick
import QtQuick.Window
import Quickshell
import "./services"
import "./lock"
ShellRoot {
Window { visible: true; width: 1200; height: 800
  LockStyleHost { id: classic; width: 600; height: 800; style: "classic" }
  LockStyleHost { id: mainframe; x: 600; width: 600; height: 800; style: "mainframe" }
}
Timer { interval: 600; running: true; onTriggered: {
  if (SettingsService.loaded && classic.ready && mainframe.ready) console.log("YOZORA_GREETER_VALID")
  else console.error("YOZORA_GREETER_INVALID")
  Qt.quit()
} }
}''')
        try:
            result = subprocess.run(['qs', '--path', str(harness)], env=env, capture_output=True, text=True, timeout=10)
            output = result.stdout + result.stderr
            if result.returncode or 'YOZORA_GREETER_VALID' not in output or any(
                    problem in output for problem in ('ReferenceError', 'TypeError', 'Failed to load configuration')):
                raise ValueError('Greeter render validation failed: ' + output[-4000:])
            result = subprocess.run(['Hyprland', '--verify-config', '--config', str(bundle / 'hyprland.lua')],
                                    check=True, capture_output=True, env=env, cwd=root)
        finally:
            harness.unlink(missing_ok=True)


def atomic(path, contents, mode=0o644):
    descriptor, temporary = tempfile.mkstemp(prefix='.yozora-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(contents)
            os.fchmod(handle.fileno(), mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def verify_greeter_account(code=CODE, data=DATA):
    """Render as the actual greeter user without accessing a seat or logging in."""
    greeter = pwd.getpwnam('greeter')
    with tempfile.TemporaryDirectory(prefix='yozora-greeter-permissions-') as temporary:
        root = Path(temporary)
        os.chown(root, greeter.pw_uid, greeter.pw_gid)
        (root / 'runtime').mkdir(mode=0o700)
        os.chown(root / 'runtime', greeter.pw_uid, greeter.pw_gid)
        env = dict(os.environ, HOME=temporary, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                   QT_QPA_PLATFORMTHEME='', YOZORA_GREETER_PREVIEW='1', YOZORA_GREETER_PREVIEW_TIMEOUT='1',
                   YOZORA_GREETER_DATA=str(data), XDG_RUNTIME_DIR=str(root / 'runtime'),
                   XDG_CONFIG_HOME=str(root / 'config'), XDG_STATE_HOME=str(root / 'state'),
                   XDG_DATA_HOME=str(root / 'share'), XDG_CACHE_HOME=str(root / 'cache'))
        for key in ('GREETD_SOCK', 'WAYLAND_DISPLAY', 'HYPRLAND_INSTANCE_SIGNATURE',
                    'DBUS_SESSION_BUS_ADDRESS', 'YOZORA_GREETER_PREVIEW_CAPTURE', 'YOZORA_GREETER_CONFIG'):
            env.pop(key, None)
        result = subprocess.run(['qs', '--path', str(code / 'preview.qml')], env=env,
                                user=greeter.pw_uid, group=greeter.pw_gid, extra_groups=[],
                                capture_output=True, text=True, timeout=15)
        output = result.stdout + result.stderr
        if result.returncode or 'YOZORA_PREVIEW_READY' not in output or any(
                problem in output for problem in ('ReferenceError', 'TypeError', 'Failed to load configuration')):
            raise ValueError('Greeter-account preview failed: ' + output[-4000:])
    print('Preview rendered successfully as the greeter account, without access to the desktop home.')


def exchange(source, destination):
    if not destination.exists():
        source.replace(destination)
        return
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.renameat2(-100, os.fsencode(source), -100, os.fsencode(destination), 2) != 0:
        raise OSError(ctypes.get_errno(), 'Could not atomically replace the installed greeter')


def apply_install(bundle, code=CODE, data=DATA, config=CONFIG):
    if os.geteuid() != 0:
        raise ValueError('System integration requires root')
    manifest = inventory(bundle)
    account_config = json.loads((bundle / 'config.json').read_text())
    account = pwd.getpwuid(account_config['uid'])
    if account.pw_uid < 1000 or account.pw_name != account_config['user']:
        raise ValueError('Expected a non-root desktop account')
    for path in (code, data, config, data / 'users', data / 'backups'):
        if path.is_symlink():
            raise ValueError('Refusing symlinked system integration path: ' + str(path))
    record_file = data / 'installation.json'
    previous = json.loads(record_file.read_text()) if record_file.exists() else None
    if code.exists() and not previous:
        raise ValueError('Existing unmanaged Yozora greeter directory; left untouched')
    if previous and previous.get('active') and current_command(config) != COMMAND:
        raise ValueError('Login command was edited outside Yozora; refusing to overwrite it')
    replacement = replace_command(config.read_text(), COMMAND)
    old_metadata = {path: path.read_bytes() if path.exists() else None
                    for path in (record_file, data / 'enabled.json', config)}
    data.mkdir(parents=True, exist_ok=True, mode=0o755)
    data.chmod(0o755)
    backups = data / 'backups'
    backups.mkdir(exist_ok=True, mode=0o700)
    backups.chmod(0o700)
    original = previous.get('original') if previous and previous.get('active') else None
    if not original:
        original = 'config-' + str(time.time_ns()) + '.toml'
        atomic(backups / original, config.read_bytes(), 0o600)
    users = data / 'users'
    users.mkdir(exist_ok=True, mode=0o755)
    profile = users / str(account.pw_uid)
    if profile.is_symlink():
        raise ValueError('Appearance directory is a symlink')
    profile.mkdir(exist_ok=True, mode=0o755)
    os.chown(profile, account.pw_uid, account.pw_gid)
    profile.chmod(0o755)
    code.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.yozora-install-', dir=code.parent) as temporary:
        staged = Path(temporary) / 'greeter'
        shutil.copytree(bundle, staged)
        for path in [staged, *staged.rglob('*')]:
            os.chown(path, 0, 0)
            path.chmod(0o755 if path.is_dir() or path.suffix == '.sh' else 0o644)
        exchange(staged, code)
        try:
            verify_greeter_account(code, data)
            atomic(record_file, (json.dumps({'version': 1, 'active': True, 'uid': account.pw_uid,
                   'original': original, 'files': manifest}, indent=2) + '\n').encode())
            atomic(data / 'enabled.json', json.dumps({'uid': account.pw_uid}).encode())
            atomic(config, replacement.encode(), config.stat().st_mode & 0o777)
        except BaseException:
            if staged.exists():
                exchange(staged, code)
            elif code.exists():
                shutil.rmtree(code)
            for path, contents in old_metadata.items():
                if contents is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic(path, contents)
            raise
    print('Yozora boot login installed for', account.pw_name)
    print('Original greetd config:', backups / original)
    print('No services restarted. Reboot when convenient to use Yozora at boot.')


def apply_remove(code=CODE, data=DATA, config=CONFIG):
    if os.geteuid() != 0:
        raise ValueError('System integration requires root')
    record_file = data / 'installation.json'
    record = json.loads(record_file.read_text())
    if not record.get('active'):
        print('Yozora greeter integration is already removed.')
        return
    if current_command(config) != COMMAND:
        raise ValueError('greetd command was edited; restore it manually rather than overwriting those changes')
    original = record['original']
    if Path(original).name != original:
        raise ValueError('Invalid original backup path')
    backup = data / 'backups' / original
    restored = backup.read_bytes()
    tomllib.loads(restored.decode())
    atomic(config, restored, config.stat().st_mode & 0o777)
    (data / 'enabled.json').unlink(missing_ok=True)
    if code.exists():
        # Preserve installed code too, including any administrator edits.
        preserved = data / 'backups' / ('greeter-code-' + str(time.time_ns()))
        shutil.copytree(code, preserved, symlinks=True)
        shutil.rmtree(code)
    record['active'] = False
    atomic(record_file, (json.dumps(record, indent=2) + '\n').encode())
    print('Previous greetd configuration restored. Appearance snapshots retained for recovery.')


def check(code=CODE, data=DATA, config=CONFIG):
    errors = []
    record_file = data / 'installation.json'
    if not record_file.exists():
        return ['Yozora boot login is not installed.']
    record = json.loads(record_file.read_text())
    if not record.get('active'):
        return ['Yozora boot login is not active.']
    if current_command(config) != COMMAND:
        errors.append('greetd is not configured to use Yozora.')
    for relative, digest in record['files'].items():
        path = code / relative
        if (not path.is_file() or path.is_symlink() or path.stat().st_uid != 0
                or path.stat().st_mode & 0o022
                or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            errors.append('Installed greeter file differs or has unsafe ownership: ' + relative)
    profile = data / 'users' / str(record['uid'])
    if profile.is_symlink() or not profile.is_dir() or profile.stat().st_uid != record['uid']:
        errors.append('Appearance publishing directory has incorrect ownership.')
    if not (profile / 'appearance.json').is_file():
        errors.append('No appearance snapshot published yet; reload the installed Yozora shell.')
    return errors


def main(command, dry_run=False, yes=False, config_dir=None):
    if os.geteuid() == 0:
        raise ValueError('Run installer commands as the desktop user, without sudo')
    if command == 'greeter-check':
        errors = check()
        print('\n'.join(errors) if errors else 'Yozora boot login files, greetd command and appearance snapshot verified.')
        return bool(errors)
    if command == 'greeter-uninstall':
        print('Restore the saved greetd configuration; preserve greeter code and appearance backups.')
        if dry_run:
            return 0
        if not yes and input('Restore the previous boot login? [y/N] ').lower() != 'y':
            return 0
        subprocess.run(['sudo', 'python3', '-B', str(Path(__file__).resolve()), 'apply-remove'], check=True)
        return 0
    required = ('qs', 'Hyprland', 'dbus-run-session', 'agreety', 'start-hyprland', 'systemd-cat', 'sudo')
    missing = [tool for tool in required if not shutil.which(tool)]
    if missing:
        raise ValueError('Install required login dependencies first: ' + ', '.join(missing))
    if not Path('/usr/lib/qt6/qml/Quickshell/Services/Greetd').is_dir():
        raise ValueError('QuickShell needs its Greetd service module')
    pwd.getpwnam('greeter')
    if not CONFIG.is_file():
        raise ValueError('Set up greetd before enabling the Yozora greeter; no other display manager is replaced automatically')
    print('Boot login:', current_command())
    print('New greeter:', COMMAND)
    print('Account:', pwd.getpwuid(os.getuid()).pw_name)
    print('Shared appearance:', DATA / 'users' / str(os.getuid()))
    print('Only appearance is shared. PAM stays unchanged; no auto-login or service restart. Activation is at the next boot.')
    if dry_run:
        return 0
    if not yes and input('Back up greetd and enable Yozora for the next login? [y/N] ').lower() != 'y':
        return 0
    with tempfile.TemporaryDirectory(prefix='yozora-greeter-stage-') as temporary:
        staged = Path(temporary) / 'greeter'
        stage_bundle(staged, os.getuid())
        validate_bundle(staged)
        subprocess.run(['sudo', 'python3', '-B', str(Path(__file__).resolve()), 'apply-install', str(staged)], check=True)
    desktop = (config_dir or Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')) / 'quickshell'
    if (desktop / 'services/GreeterSyncService.qml').is_file():
        result = subprocess.run(['qs', 'ipc', '--path', str(desktop), 'call', 'shell', 'reload'],
                                capture_output=True, text=True)
        if result.returncode:
            print('Reload the installed Yozora shell to publish the login appearance.')
    else:
        print('Deploy the updated QuickShell configuration, then reload it to enable automatic appearance sync.')
    return 0


if __name__ == '__main__':
    try:
        if sys.argv[1] == 'apply-install':
            apply_install(Path(sys.argv[2]))
        elif sys.argv[1] == 'apply-remove':
            apply_remove()
        else:
            raise ValueError('Use install.sh greeter-install, greeter-check or greeter-uninstall')
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('Greeter:', error, file=sys.stderr)
        raise SystemExit(1)
