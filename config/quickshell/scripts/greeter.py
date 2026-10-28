#!/usr/bin/env python3
"""Publish appearance data only; the boot greeter never reads the private home."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import sys
import tempfile

DATA = Path('/var/lib/yozora-greeter')
CODE = Path('/usr/local/share/yozora-greeter')
MAX_IMAGE = 32 * 1024 * 1024
COLOR_KEYS = ('background', 'surface', 'surfaceHover', 'border', 'text', 'textMuted',
              'accent', 'accentHover', 'accentText', 'red', 'green', 'yellow', 'blue')


def text(value, fallback='', limit=160):
    return ''.join(c for c in str(value or fallback) if c.isprintable())[:limit]


def normalize(payload):
    """Whitelist public appearance; never pass settings files through wholesale."""
    settings = payload.get('settings', {})
    if not isinstance(settings, dict):
        settings = {}
    def number(key, default, lower, upper):
        value = settings.get(key, default)
        return max(lower, min(upper, value)) if type(value) in (int, float) else default
    colors = payload.get('colors', {})
    if not isinstance(colors, dict):
        colors = {}
    return {
        'version': 1,
        'name': text(payload.get('name'), 'Yozora'),
        'settings': {
            'lockStyle': 'mainframe' if settings.get('lockStyle') == 'mainframe' else 'classic',
            'lockClock': 'inline' if settings.get('lockClock') == 'inline' else 'stacked',
            'clockFormat': settings.get('clockFormat') if settings.get('clockFormat') in
                           ('HH:mm', 'HH:mm:ss', 'hh:mm AP', 'hh:mm:ss AP') else 'HH:mm',
            'clockShowsDate': settings.get('clockShowsDate') is True,
            'clockShowsSeconds': settings.get('clockShowsSeconds') is True,
            'lockBlur': number('lockBlur', 32, 0, 64),
            'motionScale': number('motionScale', 100, 0, 200),
            'motionCurve': settings.get('motionCurve') if settings.get('motionCurve') in
                           ('OutCubic', 'OutQuint', 'OutBack', 'Linear') else 'OutCubic',
            'fontFamily': text(settings.get('fontFamily'), 'Liberation Sans'),
            'fontMono': text(settings.get('fontMono'), 'Liberation Mono'),
        },
        'colors': {key: value for key, value in colors.items()
                   if key in COLOR_KEYS and isinstance(value, str)
                   and re.fullmatch(r'#[0-9a-fA-F]{6}', value)},
    }


def read_json(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor) as stream:
        status = os.fstat(stream.fileno())
        if not stat.S_ISREG(status.st_mode) or status.st_size > 65536:
            raise ValueError('Appearance file must be a small regular JSON file')
        result = json.load(stream)
        if not isinstance(result, dict):
            raise ValueError('Expected an appearance object')
        return result


def atomic(path, contents):
    descriptor, temporary = tempfile.mkstemp(prefix='.publish-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(contents)
            stream.flush()
            os.fchmod(stream.fileno(), 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def image_asset(source, directory):
    if not source:
        return ''
    with open(source, 'rb') as stream:
        status = os.fstat(stream.fileno())
        if not stat.S_ISREG(status.st_mode) or status.st_size > MAX_IMAGE:
            raise ValueError('Login appearance images must be regular files up to 32 MiB')
        contents = stream.read(MAX_IMAGE + 1)
    if len(contents) > MAX_IMAGE:
        raise ValueError('Login image exceeds 32 MiB')
    if contents.startswith(b'\x89PNG\r\n\x1a\n'):
        extension = 'png'
    elif contents.startswith(b'\xff\xd8\xff'):
        extension = 'jpg'
    elif contents.startswith(b'RIFF') and contents[8:12] == b'WEBP':
        extension = 'webp'
    else:
        raise ValueError('Login images must be PNG, JPEG or WebP')
    name = 'asset-' + hashlib.sha256(contents).hexdigest() + '.' + extension
    destination = directory / name
    if not destination.exists():
        atomic(destination, contents)
    return name


def profile_directory(data=DATA, uid=None):
    return data / 'users' / str(os.getuid() if uid is None else uid)


def installed(data=DATA):
    directory = profile_directory(data)
    try:
        registered = read_json(data / 'enabled.json').get('uid') == os.getuid()
    except (OSError, ValueError):
        registered = False
    return (registered and not directory.is_symlink() and directory.is_dir()
            and directory.stat().st_uid == os.getuid()
            and os.access(directory, os.W_OK))


def publish(payload, data=DATA):
    if not installed(data):
        return False
    directory = profile_directory(data)
    descriptor = os.open(directory / '.publish.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as lock:
        if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
            raise ValueError('Appearance lock must be a regular file')
        fcntl.flock(lock, fcntl.LOCK_EX)
        return publish_locked(payload, directory)


def publish_locked(payload, directory):
    document = normalize(payload)
    old = {}
    try:
        old = read_json(directory / 'appearance.json')
    except (OSError, ValueError):
        pass
    # Failed copies do not discard the last valid shared image.
    for key in ('wallpaper', 'avatar'):
        try:
            document[key] = image_asset(payload.get(key), directory)
        except (OSError, ValueError):
            document[key] = old.get(key, '')
    contents = (json.dumps(document, indent=2, ensure_ascii=False) + '\n').encode()
    path = directory / 'appearance.json'
    if not path.is_file() or path.read_bytes() != contents:
        atomic(path, contents)
    keep = {document.get(k) for k in ('wallpaper', 'avatar')} | {old.get(k) for k in ('wallpaper', 'avatar')}
    for asset in directory.glob('asset-*'):
        if asset.name not in keep and asset.is_file() and not asset.is_symlink():
            asset.unlink()
    return True


def read_public(config=CODE / 'config.json', data=DATA):
    machine = read_json(config)
    uid = machine['uid']
    if type(uid) is not int or uid < 1000:
        raise ValueError('Invalid configured desktop user')
    account = pwd.getpwuid(uid)
    if account.pw_name != machine['user']:
        raise ValueError('Login account changed; reinstall greeter integration')
    directory = profile_directory(data, uid)
    try:
        if directory.is_symlink():
            raise ValueError('Appearance directory must not be a symlink')
        raw = read_json(directory / 'appearance.json')
    except (OSError, ValueError):
        raw = {}
    appearance = normalize(raw)
    appearance['name'] = text(raw.get('name'), account.pw_gecos.split(',')[0] or account.pw_name)
    for key in ('wallpaper', 'avatar'):
        name = raw.get(key, '')
        path = directory / name if isinstance(name, str) else directory
        valid = (isinstance(name, str) and re.fullmatch(r'asset-[0-9a-f]{64}\.(png|jpg|webp)', name)
                 and not path.is_symlink() and path.is_file() and path.stat().st_size <= MAX_IMAGE)
        appearance[key] = path.as_uri() if valid else ''
    return {'user': account.pw_name, 'uid': uid, 'appearance': appearance}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'sync', 'read'))
    parser.add_argument('payload', nargs='?')
    parser.add_argument('--config', type=Path, default=CODE / 'config.json')
    parser.add_argument('--data', type=Path, default=DATA)
    args = parser.parse_args()
    if args.action == 'status':
        print(json.dumps({'installed': installed(args.data)}))
    elif args.action == 'sync':
        if args.payload is None or len(args.payload) > 65536:
            parser.error('Expected a small appearance payload')
        publish(json.loads(args.payload), args.data)
    else:
        print(json.dumps(read_public(args.config, args.data)))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('Login appearance:', error, file=sys.stderr)
        raise SystemExit(1)
