"""Public appearance, reversible setup and actual QuickShell greetd IPC."""
import importlib.util
import json
import os
from pathlib import Path
import pwd
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

backend = module('greeter_backend', REPO / 'config/quickshell/scripts/greeter.py')
setup = module('greeter_setup', REPO / 'install/greeter.py')


class AppearanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='yozora-data-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = backend.profile_directory(self.root)
        self.directory.mkdir(parents=True)
        (self.root / 'enabled.json').write_text(json.dumps({'uid': os.getuid()}))
        self.config = self.root / 'config.json'
        self.config.write_text(json.dumps({'uid': os.getuid(), 'user': pwd.getpwuid(os.getuid()).pw_name}))

    def test_exports_only_appearance_and_copies_private_images(self):
        private = self.root / 'private.png'
        private.write_bytes(b'\x89PNG\r\n\x1a\nimage fixture')
        payload = {'name': 'Test User', 'settings': {'lockStyle': 'mainframe', 'secret': 'no'},
                   'colors': {'accent': '#abcdef', 'password': 'no'}, 'password': 'no', 'wallpaper': str(private)}
        self.assertTrue(backend.publish(payload, self.root))
        document = backend.read_json(self.directory / 'appearance.json')
        self.assertNotIn('password', document)
        self.assertNotIn('secret', document['settings'])
        self.assertEqual(document['settings']['lockStyle'], 'mainframe')
        self.assertEqual(document['colors'], {'accent': '#abcdef'})
        self.assertEqual((self.directory / document['wallpaper']).read_bytes(), private.read_bytes())
        before = (self.directory / 'appearance.json').stat().st_mtime_ns
        backend.publish(payload, self.root)
        self.assertEqual((self.directory / 'appearance.json').stat().st_mtime_ns, before)
        private.unlink()
        backend.publish(payload, self.root)
        self.assertEqual(backend.read_json(self.directory / 'appearance.json')['wallpaper'], document['wallpaper'])

    def test_public_reader_rejects_paths_and_malformed_settings(self):
        (self.directory / 'appearance.json').write_text(json.dumps({
            'settings': {'lockStyle': '../malicious.qml'}, 'avatar': '/etc/passwd',
            'wallpaper': '../../private.png', 'colors': {'accent': 'javascript:bad'}}))
        result = backend.read_public(self.config, self.root)['appearance']
        self.assertEqual(result['settings']['lockStyle'], 'classic')
        self.assertEqual(result['wallpaper'], '')
        self.assertEqual(result['avatar'], '')
        self.assertEqual(result['colors'], {})
        (self.directory / 'appearance.json').write_text('invalid JSON')
        self.assertEqual(backend.read_public(self.config, self.root)['appearance']['settings']['lockStyle'], 'classic')

    def test_clock_formats_match_the_session_clock(self):
        for value in ('HH:mm', 'hh:mm AP', 'HH:mm:ss', 'hh:mm:ss AP'):
            self.assertEqual(backend.normalize({'settings': {'clockFormat': value}})['settings']['clockFormat'], value)
        self.assertEqual(backend.normalize({})['settings']['clockFormat'], 'HH:mm')

    def test_absent_registration_and_symlink_profile_do_not_publish(self):
        (self.root / 'enabled.json').unlink()
        self.assertFalse(backend.publish({}, self.root))
        (self.root / 'enabled.json').write_text(json.dumps({'uid': os.getuid()}))
        self.directory.rmdir()
        self.directory.symlink_to(self.root)
        self.assertFalse(backend.publish({}, self.root))


class SetupTests(unittest.TestCase):
    def test_only_greetd_default_command_changes(self):
        contents = '[terminal]\nvt = 1\n\n[default_session]\ncommand = "old"\nuser = "greeter"\n'
        changed = setup.replace_command(contents, setup.COMMAND)
        self.assertEqual(changed.replace(json.dumps(setup.COMMAND), '"old"'), contents)

    def test_install_reinstall_and_uninstall_preserve_original_and_manual_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / 'greetd.toml'
            original = '[terminal]\nvt=1\n[default_session]\ncommand="noctalia-original"\nuser="greeter"\n'
            config.write_text(original)
            bundle = root / 'bundle'
            bundle.mkdir()
            (bundle / 'session.sh').write_text('#!/bin/sh\n')
            (bundle / 'config.json').write_text(json.dumps({'uid': os.getuid(), 'user': pwd.getpwuid(os.getuid()).pw_name}))
            code, data = root / 'code', root / 'data'
            with patch.object(setup.os, 'geteuid', return_value=0), patch.object(setup.os, 'chown'), \
                    patch.object(setup, 'verify_greeter_account'):
                setup.apply_install(bundle, code, data, config)
                first = json.loads((data / 'installation.json').read_text())['original']
                setup.apply_install(bundle, code, data, config)
                self.assertEqual(json.loads((data / 'installation.json').read_text())['original'], first)
                config.write_text(original.replace('noctalia-original', 'manual-change'))
                with self.assertRaisesRegex(ValueError, 'edited'):
                    setup.apply_remove(code, data, config)
                self.assertIn('manual-change', config.read_text())
                config.write_text(setup.replace_command(original, setup.COMMAND))
                setup.apply_remove(code, data, config)
                self.assertEqual(config.read_text(), original)
                self.assertFalse(code.exists())
                self.assertFalse((data / 'enabled.json').exists())
                self.assertTrue(list((data / 'backups').glob('greeter-code-*')))

    def test_failed_activation_rolls_back_code_configuration_and_registration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / 'greetd.toml'
            config.write_text('[default_session]\ncommand="original"\nuser="greeter"\n')
            before = config.read_bytes()
            bundle = root / 'bundle'
            bundle.mkdir()
            (bundle / 'config.json').write_text(json.dumps({'uid': os.getuid(), 'user': pwd.getpwuid(os.getuid()).pw_name}))
            code, data = root / 'code', root / 'data'
            real_atomic = setup.atomic
            def fail_config(path, contents, mode=0o644):
                if path == config and setup.COMMAND.encode() in contents:
                    raise OSError('simulated write failure')
                real_atomic(path, contents, mode)
            with patch.object(setup.os, 'geteuid', return_value=0), patch.object(setup.os, 'chown'), \
                    patch.object(setup, 'atomic', side_effect=fail_config), \
                    patch.object(setup, 'verify_greeter_account'):
                with self.assertRaisesRegex(OSError, 'simulated'):
                    setup.apply_install(bundle, code, data, config)
            self.assertEqual(config.read_bytes(), before)
            self.assertFalse(code.exists())
            self.assertFalse((data / 'enabled.json').exists())
            self.assertFalse((data / 'installation.json').exists())


class LauncherTests(unittest.TestCase):
    def test_ui_failure_requests_exit_but_successful_handoff_does_not_request_it_twice(self):
        for handoff in (False, True):
            with self.subTest(handoff=handoff), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / 'qs').write_text('#!/bin/sh\nexit 1\n')
                (root / 'hyprctl').write_text('#!/bin/sh\nprintf "exit\\n" >> "$TEST_EXIT_LOG"\n')
                for name in ('qs', 'hyprctl'):
                    (root / name).chmod(0o755)
                if handoff:
                    (root / 'yozora-handoff').touch()
                env = dict(os.environ, PATH=temporary + os.pathsep + os.environ['PATH'],
                           XDG_RUNTIME_DIR=temporary, TEST_EXIT_LOG=str(root / 'requests'))
                subprocess.run(['sh', str(REPO / 'greeter/run-ui.sh')], env=env, check=True)
                self.assertEqual((root / 'requests').exists(), not handoff)
                self.assertEqual((root / 'yozora-ui-failed').exists(), not handoff)

    def run_session(self, handoff):
        temporary = tempfile.TemporaryDirectory(prefix='yozora-launch-test-')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        fake = root / 'bin'
        fake.mkdir()
        # Substitute only the external greeter program; no real authentication
        # service or compositor can be reached by this launcher fixture.
        (fake / 'dbus-run-session').write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
Path(os.environ['TEST_ARGS']).write_text(json.dumps(sys.argv[1:]))
print('Hyprland startup text which must not reach the console')
if os.environ['TEST_HANDOFF'] == '1':
    Path(os.environ['XDG_RUNTIME_DIR'], 'yozora-handoff').touch()
''')
        (fake / 'agreety').write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
Path(os.environ['TEST_FALLBACK']).write_text(json.dumps(sys.argv[1:]))
''')
        (fake / 'logger').write_text('#!/bin/sh\nexit 0\n')
        for path in fake.iterdir(): path.chmod(0o755)
        script = root / 'session.sh'
        script.write_text((REPO / 'greeter/session.sh').read_text().replace('/usr/bin/agreety', str(fake / 'agreety')))
        env = dict(os.environ, PATH=str(fake) + os.pathsep + os.environ['PATH'], TEST_HANDOFF=str(int(handoff)),
                   TEST_ARGS=str(root / 'args.json'), TEST_FALLBACK=str(root / 'fallback.json'))
        env.pop('GREETD_SOCK', None)
        result = subprocess.run(['sh', str(script)], env=env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((root / 'args.json').read_text()),
                         ['--', '/usr/bin/start-hyprland', '--', '--config', str(root / 'hyprland.lua')])
        return root, result

    def test_greeter_uses_watchdog_and_forwards_isolated_config_without_console_logs(self):
        root, result = self.run_session(True)
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.stderr, '')
        self.assertFalse((root / 'fallback.json').exists())

    def test_text_login_fallback_uses_the_same_quiet_desktop_launcher(self):
        root, result = self.run_session(False)
        self.assertEqual(json.loads((root / 'fallback.json').read_text()),
                         ['--cmd', str(root / 'start-desktop.sh')])

    @unittest.skipUnless(shutil.which('systemd-cat') and shutil.which('start-hyprland'), 'Systemd and Hyprland required')
    def test_real_desktop_launcher_keeps_startup_output_off_console(self):
        with tempfile.TemporaryDirectory(prefix='yozora-watchdog-test-') as temporary:
            root = Path(temporary)
            (root / 'runtime').mkdir(mode=0o700)
            env = dict(os.environ, HOME=temporary, XDG_RUNTIME_DIR=str(root / 'runtime'),
                       XDG_CONFIG_HOME=str(root / 'config'), XDG_CACHE_HOME=str(root / 'cache'),
                       XDG_STATE_HOME=str(root / 'state'))
            env.pop('WAYLAND_DISPLAY', None)
            env.pop('HYPRLAND_INSTANCE_SIGNATURE', None)
            result = subprocess.run(['sh', str(REPO / 'greeter/start-desktop.sh'), '--', '--verify-config',
                                     '--config', str(REPO / 'greeter/hyprland.lua')],
                                    env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, '')
            self.assertEqual(result.stderr, '')


@unittest.skipUnless(shutil.which('qs'), 'QuickShell required')
class GreeterIntegrationTests(unittest.TestCase):
    def test_desktop_automatically_coalesces_style_and_wallpaper_publication(self):
        with tempfile.TemporaryDirectory(prefix='yozora-auto-sync-') as temporary:
            root = Path(temporary)
            for folder in ('services', 'theme', 'scripts', 'runtime'):
                (root / folder).mkdir(mode=0o700)
            shutil.copy2(REPO / 'config/quickshell/services/GreeterSyncService.qml', root / 'services/GreeterSyncService.qml')
            settings = {'lockStyle': 'classic', 'lockClock': 'stacked', 'clockFormat': 'hh:mm',
                        'clockShowsDate': False, 'clockShowsSeconds': False, 'lockBlur': 32,
                        'motionScale': 100, 'motionCurve': 'OutCubic', 'arrived': True}
            properties = '\n'.join('property ' + ('bool' if type(v) is bool else 'int' if type(v) is int else 'string')
                                   + ' ' + k + ': ' + json.dumps(v) for k, v in settings.items())
            stubs = {
                'SettingsService': properties,
                'ThemeService': 'property string activeId: "adaptive"; property var dynamicColors: null',
                'AccountService': 'property string name: "Test User"; property string avatar: ""; property int revision: 0',
                'WallpaperService': 'property string currentWallpaper: "old.png"; signal applied(string path)',
            }
            for name, body in stubs.items():
                (root / 'services' / (name + '.qml')).write_text('pragma Singleton\nimport QtQuick\nQtObject { ' + body + ' }')
            (root / 'theme/Theme.qml').write_text('''pragma Singleton
import QtQuick
QtObject {
property var tokens: ["accent"]
property color accent: "#112233"
property string fontFamily: "Liberation Sans"
property string fontMono: "Liberation Mono"
}''')
            (root / 'scripts/greeter.py').write_text('''import json,sys
from pathlib import Path
if sys.argv[1] == 'status': print('{"installed":true}')
else:
    with (Path(__file__).parents[1] / 'published.jsonl').open('a') as f:
        f.write(json.dumps(json.loads(sys.argv[2])) + '\\n')
''')
            (root / 'shell.qml').write_text('''import QtQuick
import Quickshell
import "./services"
import "./theme"
ShellRoot {
Component.onCompleted: { void GreeterSyncService.installed }
Timer { interval: 900; running: true; onTriggered: {
    SettingsService.lockStyle = "mainframe"
    SettingsService.lockBlur = 40
    WallpaperService.currentWallpaper = "new.png"
    WallpaperService.applied("new.png")
    Theme.accent = "#445566"
    ThemeService.dynamicColors = ({accent: "#445566"})
    finish.start()
} }
Timer { id: finish; interval: 900; onTriggered: Qt.quit() }
}''')
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                       XDG_RUNTIME_DIR=str(root / 'runtime'))
            env.pop('WAYLAND_DISPLAY', None)
            env.pop('HYPRLAND_INSTANCE_SIGNATURE', None)
            result = subprocess.run(['qs', '--path', str(root)], env=env, capture_output=True, text=True, timeout=5)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertNotIn('ReferenceError', output)
            self.assertNotIn('TypeError', output)
            records = [json.loads(line) for line in (root / 'published.jsonl').read_text().splitlines()]
            self.assertEqual(len(records), 2, output)
            self.assertEqual(records[-1]['settings']['lockStyle'], 'mainframe')
            self.assertEqual(records[-1]['wallpaper'], 'new.png')
            self.assertEqual(records[-1]['colors']['accent'], '#445566')

    def fixture(self, style='mainframe'):
        temporary = tempfile.TemporaryDirectory(prefix='yozora-greeter-test-')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        bundle = root / 'bundle'
        setup.stage_bundle(bundle, os.getuid())
        data = root / 'data'
        profile = backend.profile_directory(data)
        profile.mkdir(parents=True)
        (profile / 'appearance.json').write_text(json.dumps({'settings': {'lockStyle': style, 'motionScale': 0}}))
        runtime = root / 'runtime'
        runtime.mkdir(mode=0o700)
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                   YOZORA_GREETER_DATA=str(data), XDG_RUNTIME_DIR=str(runtime),
                   XDG_CACHE_HOME=str(root / 'cache'), XDG_STATE_HOME=str(root / 'state'))
        for key in ('WAYLAND_DISPLAY', 'HYPRLAND_INSTANCE_SIGNATURE', 'GREETD_SOCK'):
            env.pop(key, None)
        return root, bundle, env

    def execute(self, bundle, env, qml):
        (bundle / 'test.qml').write_text('''import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Services.Greetd
import "./services"
import "./lock"
ShellRoot {
''' + qml + '''
Timer { interval: 7000; running: true; onTriggered: { console.error("GREETER_TEST_FAILED timeout"); Qt.quit() } }
}''')
        result = subprocess.run(['qs', '--path', str(bundle / 'test.qml')], env=env,
                                capture_output=True, text=True, timeout=10)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn('GREETER_TEST_OK', output)
        for error in ('GREETER_TEST_FAILED', 'ReferenceError', 'TypeError', 'Failed to load configuration'):
            self.assertNotIn(error, output)
        return output

    def test_both_shared_designs_render_without_private_home_or_authentication(self):
        for style in ('classic', 'mainframe'):
            with self.subTest(style=style):
                root, bundle, env = self.fixture(style)
                env['YOZORA_GREETER_PREVIEW'] = '1'
                self.execute(bundle, env, '''
Window { visible: true; width: 1100; height: 700
    LockStyleHost { id: design; anchors.fill: parent; output: "test" }
}
Timer { interval: 500; running: true; onTriggered: {
    if (!SettingsService.loaded) { restart(); return }
    if (!design.ready) { console.error("GREETER_TEST_FAILED design not ready"); Qt.quit(); return }
    LockService.submit("preview-sentinel")
    if (LockService.authenticating) console.error("GREETER_TEST_FAILED authenticated in preview")
    console.log("GREETER_TEST_OK"); Qt.quit()
} }
''')

    def test_login_animation_stays_visible_until_the_final_fade(self):
        for style in ('classic', 'mainframe'):
            with self.subTest(style=style):
                root, bundle, env = self.fixture(style)
                profile = backend.profile_directory(root / 'data') / 'appearance.json'
                appearance = json.loads(profile.read_text())
                appearance['settings']['motionScale'] = 100
                profile.write_text(json.dumps(appearance))
                env['YOZORA_GREETER_PREVIEW'] = '1'
                self.execute(bundle, env, '''
Window { visible: true; width: 1100; height: 700
    LockStyleHost { id: design; anchors.fill: parent; output: "test" }
    LoginFade { id: fade }
}
function named(item, name) {
    if (item.objectName === name) return item
    for (const child of item.children ?? []) {
        const found = named(child, name)
        if (found) return found
    }
    return null
}
Timer { interval: 2500; running: true; onTriggered: {
    if (!SettingsService.loaded || !design.ready) { restart(); return }
    if (fade.opacity !== 0) console.error("GREETER_TEST_FAILED entrance never finished")
    LockService.leaving = true
    middle.start()
} }
Timer { id: middle; interval: LockService.handoffDuration / 2; onTriggered: {
    if (fade.opacity >= 1) console.error("GREETER_TEST_FAILED black before animation finishes")
    if (SettingsService.lockStyle === "mainframe") {
        const terminal = named(design, "mainframeTerminal")
        if (!terminal || terminal.opacity < 0.9)
            console.error("GREETER_TEST_FAILED terminal disappeared halfway through exit")
    }
    finish.start()
} }
Timer { id: finish; interval: LockService.handoffDuration / 2 + 100; onTriggered: {
    if (fade.opacity !== 1 || fade.color.toString() !== "#000000") {
        console.error("GREETER_TEST_FAILED login did not fade to black"); Qt.quit(); return
    }
    if (LockService.handoffDuration < 1000) console.error("GREETER_TEST_FAILED abrupt login exit")
    console.log("GREETER_TEST_OK"); Qt.quit()
} }
''')

    def test_reduced_motion_has_no_added_login_animation_delay(self):
        root, bundle, env = self.fixture()
        env['YOZORA_GREETER_PREVIEW'] = '1'
        self.execute(bundle, env, '''
Window { visible: true; width: 1100; height: 700
    LockStyleHost { id: design; anchors.fill: parent; output: "test" }
    LoginFade { id: fade }
}
Timer { interval: 400; running: true; onTriggered: {
    if (!SettingsService.loaded || !design.ready) { restart(); return }
    LockService.leaving = true
    finish.start()
} }
Timer { id: finish; interval: 40; onTriggered: {
    if (LockService.handoffDuration !== 0 || fade.opacity !== 1)
        console.error("GREETER_TEST_FAILED reduced motion still waits")
    console.log("GREETER_TEST_OK"); Qt.quit()
} }
''')

    def test_cancel_during_login_exit_restores_the_terminal(self):
        root, bundle, env = self.fixture()
        env['YOZORA_GREETER_PREVIEW'] = '1'
        self.execute(bundle, env, '''
Window { visible: true; width: 1100; height: 700
    MainframeView { id: view; anchors.fill: parent; loginMode: true; motion: 1; preview: true }
}
Timer { interval: 50; running: true; onTriggered: { view.leaving = true; cancel.start() } }
Timer { id: cancel; interval: 800; onTriggered: { view.leaving = false; finish.start() } }
Timer { id: finish; interval: 100; onTriggered: {
    if (view.outro !== 0) console.error("GREETER_TEST_FAILED cancelled exit stayed closed")
    console.log("GREETER_TEST_OK"); Qt.quit()
} }
''')

    def test_actual_greetd_ipc_cancel_failure_retry_multiple_prompts_and_launch(self):
        root, bundle, env = self.fixture()
        socket_path = root / 'greetd.sock'
        listener = socket.socket(socket.AF_UNIX)
        self.addCleanup(listener.close)
        listener.bind(str(socket_path))
        listener.listen(1)
        listener.settimeout(8)
        env['GREETD_SOCK'] = str(socket_path)
        errors, received = [], []
        def server():
            try:
                with listener.accept()[0] as connection:
                    connection.settimeout(8)
                    def read_exact(length):
                        data = b''
                        while len(data) < length:
                            part = connection.recv(length - len(data))
                            if not part: raise EOFError('greeter disconnected')
                            data += part
                        return data
                    while True:
                        request = json.loads(read_exact(struct.unpack('=I', read_exact(4))[0]))
                        received.append(request)
                        if request['type'] == 'create_session':
                            response = {'type': 'auth_message', 'auth_message_type': 'secret', 'auth_message': 'Password:'}
                        elif request['type'] == 'post_auth_message_response':
                            if request['response'] == 'bad-test-secret':
                                response = {'type': 'error', 'error_type': 'auth_error', 'description': 'Incorrect password'}
                            elif request['response'] in ('good-test-secret', 'cancel-test-secret'):
                                response = {'type': 'auth_message', 'auth_message_type': 'visible', 'auth_message': 'Challenge:'}
                            else:
                                response = {'type': 'success'}
                        else:
                            response = {'type': 'success'}
                        contents = json.dumps(response).encode()
                        connection.sendall(struct.pack('=I', len(contents)) + contents)
                        if request['type'] == 'start_session': return
            except BaseException as error:
                errors.append(error)
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        # Do not run the real compositor handoff in the test.
        (bundle / 'handoff.py').write_text('print("GREETER_TEST_OK")\n')
        output = self.execute(bundle, env, '''
property int phase: 0
Connections { target: Greetd; function onLaunched(): void { console.log("GREETER_TEST_OK"); Qt.quit() } }
Timer { interval: 20; repeat: true; running: true; onTriggered: {
    if (!SettingsService.loaded) return
    if (phase === 0) { phase = 1; LockService.submit("cancel-test-secret") }
    else if (phase === 1 && LockService.responseRequired) {
        phase = 2; LockService.changeUser(SettingsService.user)
    } else if (phase === 2 && Greetd.state === GreetdState.Inactive) {
        phase = 3; LockService.submit("bad-test-secret")
    } else if (phase === 3 && LockService.failed) { phase = 4; LockService.submit("good-test-secret") }
    else if (phase === 4 && LockService.responseRequired && LockService.echoResponse) {
        phase = 5; LockService.submit("challenge-response")
    }
} }
''')
        thread.join(timeout=2)
        self.assertFalse(errors, errors)
        self.assertEqual(received[-1], {'type': 'start_session', 'cmd': [str(bundle / 'start-desktop.sh')], 'env': []})
        self.assertEqual([r['username'] for r in received if r['type'] == 'create_session'],
                         [pwd.getpwuid(os.getuid()).pw_name] * 3)
        self.assertTrue(any(r['type'] == 'cancel_session' for r in received))
        self.assertNotIn('bad-test-secret', output)
        self.assertNotIn('good-test-secret', output)


if __name__ == '__main__':
    unittest.main()
