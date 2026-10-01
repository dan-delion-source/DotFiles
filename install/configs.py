#!/usr/bin/env python3
"""Install individual dotfile groups and restore the files they replaced."""

import argparse
import json
import os
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "config"
GROUPS = tuple(sorted(path.name for path in SOURCE.iterdir() if path.is_dir()))


def paths(group):
    source = SOURCE / group
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    state = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "dotfiles-installer" / group
    files = sorted(path for path in source.rglob("*") if path.is_file())
    return config / group, state, files


def installed_link(target, source):
    return target.is_symlink() and target.readlink() == source


def install(group):
    target_root, state, files = paths(group)
    manifest = state / "manifest.json"
    if manifest.exists():
        print(f"{group}: already installed; uninstall it before reinstalling")
        return False
    if state.exists() and any(state.iterdir()):
        print(f"{group}: saved state already exists at {state}; inspect it first", file=sys.stderr)
        return False
    if not files:
        print(f"{group}: no source files", file=sys.stderr)
        return False

    for source in files:
        relative = source.relative_to(SOURCE / group)
        target = target_root / relative
        if installed_link(target, source):
            print(f"{group}: unmanaged link already points to {source}; inspect it first", file=sys.stderr)
            return False
        if target.exists() and target.is_dir() and not target.is_symlink():
            print(f"{group}: expected a file at {target}, found a directory", file=sys.stderr)
            return False

    records = []
    try:
        (state / "backups").mkdir(parents=True, exist_ok=True)
        for source in files:
            relative = source.relative_to(SOURCE / group)
            target = target_root / relative
            backup = state / "backups" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            had_original = target.exists() or target.is_symlink()
            if had_original:
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(target), str(backup))
            records.append({"path": str(relative), "had_original": had_original})
            target.symlink_to(source)
        manifest.write_text(json.dumps({"group": group, "records": records}, indent=2) + "\n")
    except OSError as error:
        print(f"{group}: install failed: {error}; restoring files", file=sys.stderr)
        for record in reversed(records):
            target = target_root / record["path"]
            backup = state / "backups" / record["path"]
            if target.is_symlink() or target.exists():
                target.unlink()
            if record["had_original"] and (backup.exists() or backup.is_symlink()):
                shutil.move(str(backup), str(target))
        shutil.rmtree(state)
        return False
    print(f"{group}: installed {len(files)} file(s); originals saved in {state / 'backups'}")
    return True


def uninstall(group):
    target_root, state, _ = paths(group)
    manifest = state / "manifest.json"
    if not manifest.exists():
        print(f"{group}: no installer record found; nothing changed", file=sys.stderr)
        return False
    data = json.loads(manifest.read_text())
    records = data["records"]
    for record in records:
        relative = Path(record["path"])
        source = SOURCE / group / relative
        target = target_root / relative
        backup = state / "backups" / relative
        if target.exists() or target.is_symlink():
            if not installed_link(target, source):
                print(f"{group}: {target} changed since installation; no files removed", file=sys.stderr)
                return False
        if record["had_original"] and not (backup.exists() or backup.is_symlink()):
            print(f"{group}: original backup missing at {backup}; no files removed", file=sys.stderr)
            return False

    for record in reversed(records):
        relative = Path(record["path"])
        target = target_root / relative
        backup = state / "backups" / relative
        if target.is_symlink():
            target.unlink()
        if record["had_original"]:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(backup), str(target))
    manifest.unlink()
    shutil.rmtree(state)
    print(f"{group}: removed managed links and restored original files")
    return True


def status(group):
    target_root, state, files = paths(group)
    manifest = state / "manifest.json"
    if not manifest.exists():
        print(f"{group}: available")
        return
    intact = all(installed_link(target_root / source.relative_to(SOURCE / group), source) for source in files)
    print(f"{group}: {'installed' if intact else 'installed, with changed or missing links'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "uninstall", "status", "list"))
    parser.add_argument("group", nargs="?", choices=GROUPS)
    args = parser.parse_args()
    if args.action == "list":
        print("\n".join(GROUPS))
        return 0
    if args.group is None:
        parser.error("select a config group; run 'list' to see available groups")
    if args.action == "status":
        status(args.group)
        return 0
    return 0 if (install(args.group) if args.action == "install" else uninstall(args.group)) else 1


if __name__ == "__main__":
    sys.exit(main())
