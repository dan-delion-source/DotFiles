#!/usr/bin/env python3
"""Auditable, backup-first installer for an existing Arch Hyprland desktop."""
import argparse
import contextlib
import ctypes
import fcntl
import filecmp
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

REPO = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_name("dependencies.json")
WALLPAPER_REPO = "https://github.com/dan-delion-source/Wallpapers.git"
MENU_GROUPS = ("capture", "animated", "hardware")
CORE_CONFIGS = ("hypr", "quickshell", "kitty", "fastfetch", "matugen")
CONFIG_METADATA = {"AGENTS.md", "README.md", "__pycache__", ".git", ".agents", ".codex"}


class Terminal:
    """Small, dependency-free presentation layer; logs remain plain text."""
    def __init__(self):
        self.colour = sys.stdout.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"

    def heading(self, title):
        width = min(shutil.get_terminal_size((72, 24)).columns, 72)
        line = "\n" + title + " " + "─" * max(0, width - len(title) - 1)
        print(f"\033[1;36m{line}\033[0m" if self.colour else line.replace("─", "-"))

    def banner(self):
        self.heading("YOZORA / SETUP")
        print("Yozora · install, update, check, restore")


def menu():
    print("\n  1  Install\n  2  Check\n  3  Preview install\n  4  Restore\n  5  Exit\n  6  Update existing installation\n  7  Uninstall configs")
    choices = {"1": "install", "2": "check", "3": "preview", "4": "restore", "5": None, "6": "update", "7": "uninstall"}
    while True:
        answer = input("\nChoose [1–7]: ").strip()
        if answer in choices:
            return choices[answer]
        print("Choose a number from 1 to 7.")


def load_manifest(path=MANIFEST, package_dir=None):
    """Package names live in the text lists; JSON holds runtime metadata."""
    manifest = json.loads(path.read_text())
    package_dir = package_dir or REPO / "packages"
    inventory = {}
    for name in ("pacman.txt", "aur.txt"):
        group = None
        for number, raw in enumerate((package_dir / name).read_text().splitlines(), 1):
            if raw.startswith("# group: "):
                group = raw.removeprefix("# group: ").strip()
                continue
            package, _, note = raw.partition("#")
            package = package.strip()
            if not package:
                continue
            if group not in manifest["features"] or not re.fullmatch(r"[a-z0-9@_+.-]+", package):
                raise ValueError(f"Invalid package entry: {name}:{number}")
            identifier = note.strip().removeprefix("alternative: ") if note.strip().startswith("alternative: ") else package
            candidates = inventory.setdefault((group, identifier), [])
            if package in candidates:
                raise ValueError(f"Duplicate package: {package} [{group}]")
            candidates.append(package)
    for group, feature in manifest["features"].items():
        for dependency in feature["dependencies"]:
            key = (group, dependency["id"])
            if key not in inventory:
                raise ValueError(f"Missing package list entry: {group}/{key[1]}")
            dependency["packages"] = inventory.pop(key)
    if inventory:
        raise ValueError("Package entries lack runtime metadata: " + str(sorted(inventory)))
    return manifest


def wallpaper_health():
    if not shutil.which("awww"):
        return "missing", "awww is not installed"
    if not os.environ.get("WAYLAND_DISPLAY"):
        return "outside-session", "not in a Wayland session; check again after Hyprland login"
    try:
        result = run(["awww", "query"])
        if result.returncode == 0:
            return "ready", "daemon is responding"
        return "unavailable", "daemon unavailable; run awww-daemon in a terminal. " + result.stderr.strip()
    except (OSError, subprocess.SubprocessError) as error:
        return "unavailable", f"daemon query failed: {error}; run awww-daemon in a terminal"


def run(args, **kwargs):
    return subprocess.run(args, text=True, capture_output=True, timeout=30, **kwargs)


def exists(path):
    return path.exists() or path.is_symlink()


def fingerprint(path):
    """Hash contents, executable permissions and symlinks without following them."""
    if not exists(path):
        return None
    digest = hashlib.sha256()
    paths = [path] + (sorted(path.rglob("*")) if path.is_dir() and not path.is_symlink() else [])
    for item in paths:
        digest.update(str(item.relative_to(path)).encode())
        digest.update(b"\0")
        if item.is_symlink():
            digest.update(b"link\0" + os.readlink(item).encode())
        elif item.is_file():
            digest.update(f"file:{item.stat().st_mode & 0o777}\0".encode())
            with item.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
        else:
            digest.update(b"dir\0")
    return digest.hexdigest()


def inventory(directory):
    """Per-node fingerprints, retaining symlinks without descending into them."""
    if not directory.is_dir() or directory.is_symlink():
        return {".": fingerprint(directory)} if exists(directory) else {}
    return {str(p.relative_to(directory)): "directory" if p.is_dir() and not p.is_symlink() else fingerprint(p)
            for p in sorted(directory.rglob("*"))}


def baseline_files(source, installed):
    return {name: {"source": value, "installed": installed.get(name)} for name, value in source.items()}


def merge_plan(baseline, live, incoming):
    """Three-way comparison: only replace nodes unchanged since deployment."""
    actions, conflicts, resolved, blocked = [], [], set(), []
    names = set(baseline) | set(live) | set(incoming)
    shader = "lock/shaders/mainframe-crt.frag"
    rebuild = incoming.get(shader) != baseline.get(shader, {}).get("source")
    for name in sorted(names, key=lambda p: (len(Path(p).parts), p)):
        if any(name.startswith(parent + "/") for parent in blocked):
            continue
        old = baseline.get(name, {})
        current, new = live.get(name), incoming.get(name)
        descendants = {p for p in names if p.startswith(name + "/")}
        # A local directory deletion or replacement with a symlink/file owns
        # its entire subtree. Never write through that link into another tree.
        if new == "directory" and current != "directory" and current != old.get("installed"):
            if any(incoming.get(p) != baseline.get(p, {}).get("source") for p in {name} | descendants):
                conflicts.append(name)
            blocked.append(name)
            continue
        forced = name == shader + ".qsb" and rebuild
        if new == old.get("source") and not forced:
            continue
        if current == "directory" and new != "directory":
            if any(live.get(p) != baseline.get(p, {}).get("installed") for p in descendants):
                conflicts.append(name)
                blocked.append(name)
                continue
            blocked.append(name)
            resolved.update(descendants)
        if current == old.get("installed") or (current == new and not forced):
            resolved.add(name)
            if current != new or forced:
                actions.append(name)
        else:
            conflicts.append(name)
            if descendants:
                blocked.append(name)
    return {"actions": actions, "conflicts": conflicts, "resolved": resolved}


def remove(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif exists(path):
        path.unlink()


def copy(source, destination):
    if source.is_symlink():
        destination.symlink_to(os.readlink(source), target_is_directory=source.is_dir())
    elif source.is_dir():
        shutil.copytree(source, destination, symlinks=True)
    else:
        shutil.copy2(source, destination)


def publish_config(staged, destination):
    """Publish a complete tree without making a watched config path disappear.

    Linux renameat2(RENAME_EXCHANGE) swaps both names in one operation, even
    for nonempty directories or symlinks. The old tree stays at staged until
    the caller cleans its temporary directory. Fail closed on unsupported
    filesystems; remove-then-rename can trigger a broken compositor reload.
    """
    if not exists(destination):
        staged.replace(destination)
        return
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        exchange = libc.renameat2
    except AttributeError as error:
        raise ValueError("Atomic config replacement requires Linux renameat2; existing config kept") from error
    exchange.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    exchange.restype = ctypes.c_int
    if exchange(-100, os.fsencode(staged), -100, os.fsencode(destination), 2) != 0:
        error = ctypes.get_errno()
        raise OSError(error, "Atomic config replacement failed; existing config kept: " + os.strerror(error), str(destination))


def bake_lock_shader(staged):
    """Bake against the destination system's Qt shader package version."""
    source = staged / "lock/shaders/mainframe-crt.frag"
    if not source.is_file():
        return
    run(["/usr/lib/qt6/bin/qsb", "--glsl", "100 es,120,150", "--hlsl", "50",
         "--msl", "12", "-o", str(source.with_suffix(".frag.qsb")), str(source)], check=True)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


class Deployment:
    def __init__(self, repo, config, data, state, wallpaper_dir=None, discover=True):
        self.repo = repo.resolve()
        self.config, self.data, self.state = [p.absolute() for p in (config, data, state)]
        self.directory = self.state / "danshell-installer"
        self.record = self.directory / "installation.json"
        self.wallpaper_dir = (wallpaper_dir or Path.home() / "Pictures/Wallpapers").absolute()
        source_root = self.repo / "config"
        extras = (sorted(p.name for p in source_root.iterdir()
                         if p.name not in CORE_CONFIGS and p.name not in CONFIG_METADATA) if discover else [])
        self.targets = [(source_root / name, self.config / name) for name in (*CORE_CONFIGS, *extras)]
        destinations = [destination for _, destination in self.targets] + [self.wallpaper_dir, self.data / "wallpapers"]
        for destination in destinations:
            # Never mutate the checkout through live links or overlapping roots.
            resolved = destination.resolve()
            if resolved == self.repo or resolved.is_relative_to(self.repo) or self.repo.is_relative_to(resolved):
                raise ValueError(f"Destination overlaps checkout: {destination}")
            if any(parent.is_symlink() for parent in destination.parents):
                raise ValueError(f"Destination has a symlinked parent: {destination}")
            if any(destination != other and
                   (destination.is_relative_to(other) or other.is_relative_to(destination))
                   for other in destinations):
                raise ValueError("Configuration and wallpaper targets overlap")
        for directory in (self.directory,):
            resolved = directory.resolve()
            if resolved.is_relative_to(self.repo) or any(
                resolved.is_relative_to(d.resolve()) or d.resolve().is_relative_to(resolved)
                for d in destinations
            ):
                raise ValueError("Installer state must be separate from checkout and targets")

    def load(self):
        if not self.record.exists():
            return {"schema": 1, "entries": []}
        document = json.loads(self.record.read_text())
        for entry in document["entries"]:
            destination = Path(entry["destination"])
            # Retain restoration support for previously managed top-level
            # configs even when their source has since left the checkout.
            if ".." in destination.parts or (destination.parent != self.config and destination != self.data / "wallpapers"):
                raise ValueError("Installation uses different XDG directories; use the original paths")
            if entry.get("backup"):
                backup = Path(entry["backup"])
                if ".." in backup.parts or not backup.is_relative_to(self.directory):
                    raise ValueError("Invalid backup path in installation record")
                if any(p.is_symlink() for p in backup.parents if p.is_relative_to(self.directory)):
                    raise ValueError("Backup directory contains a symlink; refusing to follow it")
            if any(p.is_symlink() for p in destination.parents):
                raise ValueError("Config destination has a symlinked parent")
            resolved = destination.resolve()
            if not destination.is_symlink() and (resolved.is_relative_to(self.repo) or self.directory.resolve().is_relative_to(resolved)):
                raise ValueError("Recorded destination overlaps checkout or installer state")
            for relative in entry.get("files", {}):
                if Path(relative).is_absolute() or ".." in Path(relative).parts or (not Path(relative).parts and relative != "."):
                    raise ValueError("Invalid config path in installation record")
        wallpapers = document.get("wallpapers", {})
        if wallpapers:
            if wallpapers["directory"] != str(self.wallpaper_dir):
                raise ValueError("Wallpaper installation uses a different destination")
            for relative in wallpapers["files"]:
                parts = Path(relative).parts
                if (Path(relative).is_absolute() or ".." in parts or len(parts) not in (1, 2)
                        or (len(parts) == 2 and parts[0] != "animated")):
                    raise ValueError("Invalid wallpaper path in installation record")
        return document

    @contextlib.contextmanager
    def locked(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.directory / "lock").open("w") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise ValueError("Another installer is running") from error
            yield

    def preview(self):
        for source, destination in self.targets:
            print(f"CONFIG {source} -> {destination}")

    def preflight(self, document=None):
        document = self.load() if document is None else document
        entries = {e["destination"]: e for e in document["entries"]}
        for source, destination in self.targets:
            if source.is_symlink() or not (source.is_dir() or source.is_file()):
                raise ValueError(f"Missing or symlinked source: {source}")
            entry = entries.get(str(destination))
            if entry and (entry.get("pending") or fingerprint(destination) != entry["installed"]):
                raise ValueError(f"Changed since installation: {destination}. Use update to preserve edits, or restore first.")
            if entry and entry.get("local_changes"):
                raise ValueError(f"Local edits retained in {destination}. Use update instead of reinstalling.")

    def install(self, groups=None):
        with self.locked():
            document = self.load()
            entries = {e["destination"]: e for e in document["entries"]}
            self.preflight(document)
            batch = str(time.time_ns())
            for index, (source, destination) in enumerate(self.targets):
                wanted = fingerprint(source)
                entry = entries.get(str(destination))
                if entry and wanted == entry.get("source", entry["installed"]):
                    print(f"UNCHANGED {destination}")
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                stage = Path(tempfile.mkdtemp(prefix=".danshell-", dir=destination.parent))
                staged = stage / "config"
                try:
                    copy(source, staged)
                    if source.name == "quickshell":
                        bake_lock_shader(staged)
                    installed = fingerprint(staged)
                    files = baseline_files(inventory(source), inventory(staged))
                    if entry is None:
                        backup = self.directory / "backups" / batch / str(index)
                        backup.parent.mkdir(parents=True, exist_ok=True)
                        original = exists(destination)
                        entry = {"destination": str(destination), "backup": str(backup) if original else None,
                                 "installed": installed, "source": wanted, "pending": True}
                        if original:
                            # Copy first so a crash cannot lose the original.
                            copy(destination, backup)
                        document["entries"].append(entry)
                        save(self.record, document)
                    else:
                        entry["pending"] = True
                        save(self.record, document)
                    publish_config(staged, destination)
                    entry.update(installed=installed, source=wanted, pending=False,
                                 files=files)
                    save(self.record, document)
                    print(f"INSTALLED {destination}")
                finally:
                    remove(stage)
            if groups is not None:
                document["groups"] = sorted(set(groups) - {"wallpapers"})
                save(self.record, document)

    def plan_update(self):
        document = self.load()
        entries = {e["destination"]: e for e in document["entries"]}
        if any(str(self.config / name) not in entries for name in CORE_CONFIGS):
            raise ValueError("No complete managed installation. Run install first to back up and adopt existing configs.")
        plans = []
        for source, destination in self.targets:
            entry = entries.get(str(destination))
            if entry and entry.get("pending"):
                raise ValueError(f"Interrupted deployment: {destination}. Restore before updating.")
            if source.is_symlink() or not (source.is_dir() or source.is_file()):
                raise ValueError(f"Missing or symlinked source: {source}")
            source_hash, live_hash = fingerprint(source), fingerprint(destination)
            incoming = inventory(source)
            same_type = not destination.is_symlink() and (
                (destination.is_dir() and source.is_dir()) or (destination.is_file() and source.is_file()))
            live = inventory(destination) if same_type else ({} if not exists(destination) and entry is None else None)
            baseline = entry.get("files") if entry else {}
            if entry and baseline is None and live is not None:
                if source_hash == entry.get("source", entry["installed"]) == entry["installed"]:
                    # Legacy records with an exact source match still identify
                    # the original per-file baseline even if live files changed.
                    baseline = baseline_files(incoming, incoming)
                elif live_hash == entry["installed"]:
                    baseline = baseline_files(live, live)
            changes = merge_plan(baseline, live, incoming) if baseline is not None and live is not None else {
                "actions": [], "conflicts": ["."], "resolved": set()}
            plans.append({**changes, "source": source, "destination": destination, "entry": entry,
                          "source_hash": source_hash, "live_hash": live_hash, "incoming": incoming,
                          "live": live, "baseline": baseline, "new": entry is None})
        return plans

    def preview_update(self, plans):
        for plan in plans:
            destination = plan["destination"]
            if plan["new"]:
                print(f"ADD CONFIG {destination} (back up existing contents; keep conflicting local files)")
            if not plan["actions"] and not plan["conflicts"]:
                print(f"UNCHANGED upstream: {destination} (local-only changes kept)")
            for name in plan["actions"]:
                print(f"{'UPDATE' if name in plan['incoming'] else 'REMOVE obsolete'} {destination / name}")
            for name in plan["conflicts"]:
                reason = ("legacy baseline unavailable or config type locally replaced"
                          if name == "." and (plan["baseline"] is None or plan["live"] is None)
                          else "local edit conflicts with upstream")
                print(f"KEEP {destination / name}: {reason}; incoming version saved for review when applied")

    def update(self, plans=None, groups=None):
        """Merge owned files, preserve local changes and retain original backups."""
        with self.locked():
            plans = self.plan_update() if plans is None else plans
            document = self.load()
            entries = {e["destination"]: e for e in document["entries"]}
            for plan in plans:
                if (entries.get(str(plan["destination"])) != plan["entry"]
                        or fingerprint(plan["source"]) != plan["source_hash"]
                        or fingerprint(plan["destination"]) != plan["live_hash"]):
                    raise ValueError("Configuration changed since preview; preview the update again")
            batch = self.directory / "updates" / str(time.time_ns())
            conflicts = 0
            for plan in plans:
                source, destination = plan["source"], plan["destination"]
                entry = entries.get(str(destination))
                if plan["conflicts"]:
                    review = batch / "incoming" / destination.name
                    for relative in plan["conflicts"]:
                        candidate = source / relative
                        if exists(candidate):
                            target = review / relative
                            target.parent.mkdir(parents=True, exist_ok=True)
                            copy(candidate, target)
                    save(batch / "conflicts" / (destination.name + ".json"), {
                        "destination": str(destination), "paths": plan["conflicts"],
                        "note": "Keep local versions; an absent incoming path means upstream deleted it."})
                    conflicts += len(plan["conflicts"])
                    print(f"REVIEW incoming versions: {review}; deletion notes: {batch / 'conflicts'}")
                if plan["baseline"] is None or plan["live"] is None:
                    continue
                with tempfile.TemporaryDirectory(prefix=".danshell-", dir=destination.parent) as temporary:
                    stage = Path(temporary)
                    if plan["actions"] or (plan["new"] and not exists(destination)):
                        merged, candidate = stage / "config", stage / "incoming"
                        if exists(destination):
                            copy(destination, merged)
                        elif source.is_dir():
                            merged.mkdir()
                        copy(source, candidate)
                        if source.name == "quickshell":
                            bake_lock_shader(candidate)
                        for relative in plan["actions"]:
                            target = merged / relative
                            if any(parent.is_symlink() for parent in target.parents if parent.is_relative_to(merged)):
                                raise ValueError(f"Refusing update through a local symlink: {destination / relative}")
                            if plan["incoming"].get(relative) == "directory":
                                if not target.is_dir() or target.is_symlink():
                                    remove(target)
                                    target.mkdir(parents=True)
                            else:
                                remove(target)
                                if relative in plan["incoming"]:
                                    target.parent.mkdir(parents=True, exist_ok=True)
                                    copy(candidate / relative, target)
                        installed = inventory(merged)
                    else:
                        merged = None
                        installed = plan["live"]
                    baseline = {name: dict(value) for name, value in plan["baseline"].items()}
                    for relative in plan["resolved"]:
                        if relative in plan["incoming"]:
                            baseline[relative] = {"source": plan["incoming"][relative], "installed": installed.get(relative)}
                        else:
                            baseline.pop(relative, None)
                    # Recheck after staging: shell-generated files may have changed.
                    if (fingerprint(destination) != plan["live_hash"]
                            or fingerprint(source) != plan["source_hash"]):
                        raise ValueError("Configuration changed while staging; preview the update again")
                    backup = None
                    if (merged is not None or plan["new"]) and exists(destination):
                        backup = batch / "before" / destination.name
                        backup.parent.mkdir(parents=True, exist_ok=True)
                        copy(destination, backup)
                        if fingerprint(destination) != plan["live_hash"]:
                            raise ValueError("Configuration changed during backup; preview the update again")
                    if entry is None:
                        entry = {"destination": str(destination), "backup": str(backup) if backup else None,
                                 "source": plan["source_hash"], "installed": plan["live_hash"], "pending": False}
                        document["entries"].append(entry)
                        entries[str(destination)] = entry
                    if merged is not None:
                        installed_hash = fingerprint(merged)
                        entry["pending"] = True
                        save(self.record, document)
                        publish_config(merged, destination)
                        print(f"UPDATED {destination}" + (f"; previous copy: {backup}" if backup else "; new config"))
                    else:
                        installed_hash = plan["live_hash"]
                    entry.update(source=plan["source_hash"], installed=installed_hash, pending=False,
                                 files=baseline, local_changes=installed != {p: v["installed"] for p, v in baseline.items()})
                    save(self.record, document)
            if groups is not None:
                document["groups"] = sorted(set(groups) - {"wallpapers"})
                save(self.record, document)
            return conflicts

    def import_wallpapers(self, source):
        """Add media only. Journal each addition; never replace a user's file."""
        if not source.is_dir():
            raise ValueError("Downloaded repository has no wallpapers/ directory")
        still = {".jpg", ".jpeg", ".png", ".webp"}
        motion = {".mp4", ".webm", ".mkv", ".mov", ".gif"}
        counts = {"added": 0, "identical": 0, "conflicts": 0}
        with self.locked():
            document = self.load()
            record = document.setdefault("wallpapers", {"directory": str(self.wallpaper_dir), "files": {}})
            for item in sorted(source.rglob("*")):
                if item.is_symlink() or not item.is_file() or any(p.is_symlink() for p in item.parents):
                    continue
                suffix = item.suffix.lower()
                if suffix not in still | motion or item.name.startswith("."):
                    continue
                relative = Path("animated") / item.name if suffix in motion else Path(item.name)
                destination = self.wallpaper_dir / relative
                if any(p.is_symlink() for p in [destination.parent, *destination.parents]):
                    raise ValueError(f"Wallpaper destination has a symlinked parent: {destination}")
                if exists(destination):
                    identical = (destination.is_file() and not destination.is_symlink()
                                 and filecmp.cmp(item, destination, shallow=False))
                    counts["identical" if identical else "conflicts"] += 1
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(prefix=".danshell-", dir=destination.parent) as temporary:
                    staged = Path(temporary) / "image"
                    shutil.copyfile(item, staged)
                    staged.chmod(0o644)
                    record["files"][str(relative)] = fingerprint(staged)
                    save(self.record, document)
                    try:
                        # Atomic publication with exclusive creation, including if
                        # another process creates the destination during staging.
                        os.link(staged, destination)
                    except FileExistsError:
                        record["files"].pop(str(relative))
                        save(self.record, document)
                        counts["conflicts"] += 1
                        continue
                counts["added"] += 1
        print("WALLPAPERS " + ", ".join(f"{value} {name}" for name, value in counts.items()))
        return counts

    def download_wallpapers(self):
        print(f"Downloading optional collection: {WALLPAPER_REPO}")
        try:
            with tempfile.TemporaryDirectory(prefix="danshell-wallpapers-") as temporary:
                checkout = Path(temporary) / "collection"
                subprocess.run(["git", "clone", "--depth", "1", "--single-branch", "--branch", "main",
                                "--", WALLPAPER_REPO, str(checkout)], check=True, timeout=600)
                self.import_wallpapers(checkout / "wallpapers")
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            print(f"WALLPAPERS incomplete: {error}", file=sys.stderr)
            print("Desktop installation can continue. Retry: ./install.sh wallpapers", file=sys.stderr)
            return False
        return True

    def restore(self, dry_run=False, remove_wallpapers=True):
        if not self.record.exists():
            print("No installation record; nothing to restore.")
            return
        document = self.load()
        def selected(document):
            return [entry for entry in document["entries"] if remove_wallpapers
                    or Path(entry["destination"]) != self.data / "wallpapers"]
        # Validate every original before touching any target, so a missing
        # backup cannot cause a partly completed uninstall.
        for entry in selected(document):
            if entry.get("backup") and not exists(Path(entry["backup"])):
                raise ValueError(f"Backup missing: {entry['backup']}; configs untouched")
        if dry_run:
            for entry in reversed(selected(document)):
                print(f"RESTORE {entry['destination']} (preserve changes if present)")
            if remove_wallpapers:
                for relative in document.get("wallpapers", {}).get("files", {}):
                    print(f"REMOVE unchanged imported wallpaper: {self.wallpaper_dir / relative}")
            else:
                print("KEEP wallpapers, installed packages, services and shell runtime state")
            return
        with self.locked():
            document = self.load()
            for entry in reversed(selected(document)):
                destination = Path(entry["destination"])
                backup = Path(entry["backup"]) if entry["backup"] else None
                if backup and not exists(backup):
                    raise ValueError(f"Backup missing: {backup}; leaving {destination} untouched")
                changed = fingerprint(destination) != entry["installed"] or entry.get("pending") or entry.get("local_changes")
                if exists(destination) and changed:
                    preserved = self.directory / "preserved" / str(time.time_ns()) / destination.name
                    preserved.parent.mkdir(parents=True, exist_ok=True)
                    copy(destination, preserved)
                    print(f"PRESERVED edits: {preserved}")
                if backup:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with tempfile.TemporaryDirectory(prefix=".danshell-", dir=destination.parent) as temporary:
                        staged = Path(temporary) / "config"
                        copy(backup, staged)
                        publish_config(staged, destination)
                else:
                    remove(destination)
                document["entries"].remove(entry)
                save(self.record, document)
                print(f"RESTORED {destination}")
            wallpapers = document.get("wallpapers", {}).get("files", {}) if remove_wallpapers else {}
            for relative, installed in list(wallpapers.items()):
                destination = self.wallpaper_dir / relative
                if any(p.is_symlink() for p in destination.parents):
                    print(f"KEPT wallpaper under symlinked directory: {destination}")
                elif fingerprint(destination) == installed:
                    remove(destination)
                    print(f"REMOVED imported wallpaper: {destination}")
                elif exists(destination):
                    print(f"KEPT edited wallpaper: {destination}")
                wallpapers.pop(relative)
                save(self.record, document)
            if document["entries"] or document.get("wallpapers", {}).get("files"):
                save(self.record, document)
                print("Kept wallpaper ownership record; use uninstall --remove-wallpapers to remove unchanged imports later.")
            else:
                self.record.unlink()


def selection(manifest, names):
    chosen = {"core"} | {n.strip() for name in names for n in name.split(",") if n.strip()}
    unknown = chosen - manifest["features"].keys()
    if unknown:
        raise ValueError("Unknown groups: " + ", ".join(sorted(unknown)))
    return sorted(chosen)


def resolve_dependencies(manifest, groups):
    resolved = []
    for group in groups:
        for dependency in manifest["features"][group]["dependencies"]:
            candidates = dependency["packages"]
            installed = next((p for p in candidates if run(["pacman", "-Q", p]).returncode == 0), None)
            repository = None if installed else next(
                (p for p in candidates if run(["pacman", "-Si", p]).returncode == 0), None)
            resolved.append({**dependency, "group": group, "package": installed or repository or candidates[0],
                             "source": "installed" if installed else "repository" if repository else "AUR"})
    return resolved


def verify_aur(dependencies):
    pending = [d for d in dependencies if d["source"] == "AUR"]
    if not pending:
        return
    candidates = sorted({p for d in pending for p in d["packages"]})
    url = "https://aur.archlinux.org/rpc/v5/info?" + urllib.parse.urlencode(
        [("arg[]", p) for p in candidates])
    with urllib.request.urlopen(url, timeout=20) as response:
        data = json.load(response)
    if data.get("type") == "error":
        raise ValueError("AUR verification failed: " + data.get("error", "unknown error"))
    available = {entry["Name"] for entry in data.get("results", [])}
    for dependency in pending:
        package = next((p for p in dependency["packages"] if p in available), None)
        if not package:
            raise ValueError("Not found in repositories or AUR: " + ", ".join(dependency["packages"]))
        dependency["package"] = package


def qml_compatibility(repo):
    """Check installed module metadata and parse without instantiating a shell."""
    errors = []
    files = sorted((repo / "config/quickshell").rglob("*.qml"))
    modules = set()
    for path in files:
        modules.update(re.findall(r"^import ([\w.]+)", path.read_text(), re.M))
    bases = [Path(p) for p in os.environ.get("QML_IMPORT_PATH", "").split(os.pathsep) if p]
    bases += [Path("/usr/lib/qt6/qml"), Path("/usr/lib/qt/qml")]
    for module in sorted(modules):
        if not any((base / module.replace(".", "/") / "qmldir").is_file() for base in bases):
            errors.append(f"Missing QML module: {module}")
    # /usr/bin may contain obsolete Qt 5 tools. Prefer Qt 6 explicitly.
    formatter = next((str(p) for p in (Path("/usr/lib/qt6/bin/qmlformat"),)
                      if p.is_file()), None)
    if not formatter:
        errors.append("Missing Qt 6 qmlformat (qt6-declarative)")
    else:
        for path in files:
            result = run([formatter, "-n", str(path)])
            if result.returncode:
                # Some valid Canvas/Shape expressions trip qmlformat's
                # round-trip verification. The matching Qt 6 parser is the fallback.
                lint = Path(formatter).with_name("qmllint")
                checked = run([str(lint), "--ignore-settings", "--max-warnings", "-1", str(path)])
                if checked.returncode:
                    errors.append(f"QML parsing failed ({path.name}): " +
                                  (checked.stderr or result.stderr).strip()[:1000])
    return errors


def source_compatibility(repo):
    errors = qml_compatibility(repo)
    if not shutil.which("Hyprland"):
        return errors
    # Use the compositor's own Lua parser, without launching a compositor or
    # touching the user's state. Startup event callbacks do not run in verify mode.
    with tempfile.TemporaryDirectory(prefix="danshell-config-check-") as temporary:
        root = Path(temporary)
        shutil.copytree(repo / "config/hypr", root / "config/hypr")
        (root / "runtime").mkdir(mode=0o700)
        env = dict(os.environ, HOME=str(root), XDG_CONFIG_HOME=str(root / "config"),
                   XDG_STATE_HOME=str(root / "state"), XDG_DATA_HOME=str(root / "data"),
                   XDG_CACHE_HOME=str(root / "cache"), XDG_RUNTIME_DIR=str(root / "runtime"))
        env.pop("WAYLAND_DISPLAY", None)
        env.pop("HYPRLAND_INSTANCE_SIGNATURE", None)
        result = run(["Hyprland", "--verify-config", "--config", str(root / "config/hypr/hyprland.lua")],
                     env=env, cwd=root)
        if result.returncode:
            errors.append("Hyprland Lua config failed: " + (result.stdout + result.stderr).strip()[-2000:])
    return errors


def version_at_least(output, minimum):
    match = re.search(r"(?:v)?(\d+)\.(\d+)\.(\d+)", output)
    return bool(match and tuple(map(int, match.groups())) >= minimum)


def compatibility():
    errors = []
    for command, arguments, minimum in (
        ("Hyprland", ["--version"], (0, 56, 2)),
        ("qs", ["--version"], (0, 3, 2)),
        ("matugen", ["--version"], (4, 0, 0)),
    ):
        if not shutil.which(command):
            errors.append(f"Missing {command}")
            continue
        result = run([command, *arguments])
        if result.returncode or not version_at_least(result.stdout + result.stderr, minimum):
            errors.append(f"{command} requires >= {'.'.join(map(str, minimum))}; detected: {(result.stdout + result.stderr).strip()}")
    if shutil.which("matugen"):
        help_text = run(["matugen", "image", "--help"])
        for flag in ("--dry-run", "--json", "--source-color-index"):
            if flag not in help_text.stdout:
                errors.append(f"Matugen lacks required capability {flag}; upgrade Matugen")
    for path in ("/etc/pam.d/login", "/usr/share/unicode/emoji/emoji-test.txt",
                 "/usr/share/unicode/cldr/common/annotations/en.xml",
                 "/usr/share/iso-codes/json/iso_3166-1.json"):
        if not Path(path).is_file():
            errors.append(f"Missing runtime data: {path}")
    return errors


def platform_check():
    values = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip('"')
    if not ({values.get("ID", ""), *values.get("ID_LIKE", "").split()} & {"arch", "cachyos"}):
        raise ValueError("Supported target: an installed CachyOS/Arch system with a normal user account")
    if not shutil.which("pacman"):
        raise ValueError("pacman is required")


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("command", nargs="?", choices=("check", "install", "update", "restore", "uninstall", "wallpapers",
                     "greeter-install", "greeter-check", "greeter-uninstall"))
    cli.add_argument("--groups", action="append", default=[], help="Comma-separated optional feature groups")
    cli.add_argument("--dry-run", action="store_true", help="Read-only preview; no packages, configs or state are written")
    cli.add_argument("--yes", action="store_true", help="Accept the displayed installer plan; package manager prompts remain")
    cli.add_argument("--remove-wallpapers", action="store_true",
                     help="Uninstall: also remove unchanged installer-added wallpapers")
    wallpapers = cli.add_mutually_exclusive_group()
    wallpapers.add_argument("--wallpapers", dest="wallpapers", action="store_true", default=None,
                            help="Download the optional collection to ~/Pictures/Wallpapers")
    wallpapers.add_argument("--no-wallpapers", dest="wallpapers", action="store_false",
                            help="Skip the optional wallpaper collection")
    cli.add_argument("--config-dir", type=Path, default=Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"))
    cli.add_argument("--data-dir", type=Path, default=Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share"))
    cli.add_argument("--state-dir", type=Path, default=Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state"))
    return cli


def install_packages(dependencies):
    missing = [d for d in dependencies if d["source"] != "installed"]
    aur = sorted({d["package"] for d in missing if d["source"] == "AUR"})
    helper = next((h for h in ("paru", "yay") if shutil.which(h)), None)
    if aur and not helper:
        raise ValueError("Selected AUR packages require an existing paru/yay: " + ", ".join(aur))
    official = sorted({d["package"] for d in missing if d["source"] == "repository"})
    if official:
        subprocess.run(["sudo", "pacman", "-Syu", "--needed", *official], check=True)
    if aur:
        subprocess.run([helper, "-S", "--needed", *aur], check=True)


def main():
    cli = parser()
    args = cli.parse_args()
    terminal = Terminal()
    if args.command is None:
        if not sys.stdin.isatty():
            cli.print_help()
            return 0
        terminal.banner()
        args.command = menu()
        if args.command is None:
            return 0
        if args.command == "preview":
            args.command, args.dry_run = "install", True
    else:
        terminal.banner()
    if args.command.startswith("greeter-"):
        import importlib.util
        spec = importlib.util.spec_from_file_location("yozora_greeter_installer", REPO / "install/greeter.py")
        greeter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(greeter)
        return int(greeter.main(args.command, args.dry_run, args.yes, args.config_dir))
    deploy = Deployment(REPO, args.config_dir, args.data_dir, args.state_dir,
                        discover=args.command not in ("restore", "uninstall"))
    if args.command in ("restore", "uninstall"):
        if not args.dry_run and os.geteuid() == 0:
            raise ValueError("Run as your desktop user, without sudo")
        remove_wallpapers = args.command == "restore" or args.remove_wallpapers
        if not deploy.record.exists():
            deploy.restore(args.dry_run, remove_wallpapers=remove_wallpapers)
            return 0
        if not args.dry_run and not args.yes:
            deploy.restore(dry_run=True, remove_wallpapers=remove_wallpapers)
            if input("Restore original configs, preserving later edits in the backup folder? [y/N] ").lower() != "y":
                print("Cancelled; no changes made.")
                return 0
        deploy.restore(args.dry_run, remove_wallpapers=remove_wallpapers)
        if args.dry_run:
            print("Preview only; no files changed.")
        else:
            print("Configs uninstalled/restored. Log out and back in to use the restored setup.")
        return 0
    platform_check()
    manifest = load_manifest()
    if args.command == "wallpapers":
        print(f"Optional collection: {WALLPAPER_REPO}\nDestination: {deploy.wallpaper_dir}")
        dependencies = resolve_dependencies(manifest, ["wallpapers"])
        verify_aur(dependencies)
        for dependency in dependencies:
            print(f"{dependency['source'].upper()} {dependency['package']}")
        if args.dry_run or args.wallpapers is False:
            return 0
        if os.geteuid() == 0:
            raise ValueError("Run as your desktop user, without sudo")
        if not args.yes and input("Download this optional collection (may be large)? [y/N] ").lower() != "y":
            print("Cancelled; no changes made.")
            return 0
        install_packages(dependencies)
        return 0 if deploy.download_wallpapers() else 1
    if args.command == "install" and not args.groups and not args.yes and not args.dry_run:
        terminal.heading("1 / Choose features")
        for name in MENU_GROUPS:
            print(f"  {name}: {manifest['features'][name]['description']}")
        args.groups = [input("Optional groups (comma-separated; Enter for core only): ").strip()]
    if args.command == "install" and args.wallpapers is None and not args.yes and not args.dry_run:
        print(f"\nOptional collection: {WALLPAPER_REPO} (may be a large download)")
        args.wallpapers = input("Download to ~/Pictures/Wallpapers? [y/N] ").lower() == "y"
    update_plans = deploy.plan_update() if args.command == "update" else None
    # Every run defaults to core. Old saved app/group selections must not
    # silently opt a later update into optional package installation.
    groups = selection(manifest, args.groups)
    if "wallpapers" in groups and args.wallpapers is not True:
        groups.remove("wallpapers")
    if args.wallpapers:
        groups = sorted(set(groups) | {"wallpapers"})
    terminal.heading("2 / Packages and services")
    dependencies = resolve_dependencies(manifest, groups)
    verify_aur(dependencies)
    for dependency in dependencies:
        missing = [c for c in dependency["commands"] if not shutil.which(c)]
        print(f"{dependency['source'].upper():10} {dependency['package']} [{dependency['group']}]"
              + (f"; missing: {', '.join(missing)}" if missing else ""))
    for note in manifest["external_integrations"]:
        print(f"NOTE {note}")
    service_commands = []
    service_errors = []
    for service in manifest["services"]:
        if service["feature"] not in groups:
            continue
        command = ["systemctl"] + (["--user"] if service["scope"] == "user" else [])
        result = run([*command, "is-active", service["name"]])
        active = result.returncode == 0
        unknown = result.returncode not in (0, 3, 4)
        if unknown:
            service_errors.append(f"Cannot inspect {service['name']}: {result.stderr.strip()}")
        print(f"SERVICE {service['name']}: {'active' if active else 'unverified' if unknown else 'inactive/unavailable'}")
        if not active and not unknown:
            action = ["start"] if service.get("activation") == "dbus" else ["enable", "--now"]
            service_commands.append((["sudo"] if service["scope"] == "system" else [])
                                    + command + action + [service["name"]])
    for command in service_commands:
        print("SERVICE ACTION " + " ".join(command))
    terminal.heading("3 / Compatibility and configuration plan")
    errors = compatibility() + source_compatibility(REPO)
    for error in errors:
        print("COMPATIBILITY " + error)
    if update_plans is not None:
        deploy.preview_update(update_plans)
    else:
        deploy.preview()
    print(f"WALLPAPERS {'download ' + WALLPAPER_REPO + ' -> ' + str(deploy.wallpaper_dir) if args.wallpapers else 'skip (optional)'}")
    health, detail = wallpaper_health()
    print(f"WALLPAPER SERVICE {health}: {detail}")
    if args.command == "install":
        deploy.preflight()
    if args.command == "check":
        for error in service_errors:
            print("UNVERIFIED " + error)
        return int(bool(errors or service_errors or service_commands or health in ("missing", "unavailable") or any(d["source"] != "installed" or
                   any(not shutil.which(c) for c in d["commands"]) for d in dependencies)))
    if args.dry_run:
        print("Preview only; no packages, services or configs changed.")
        return 0
    if os.geteuid() == 0:
        raise ValueError("Run as your desktop user; sudo is used only for system packages and services")
    if service_errors:
        raise ValueError("Run installation from the target user's systemd desktop session; service checks failed")
    # Do not replace an existing network manager's live connection.
    if any("NetworkManager.service" in c for c in service_commands) and run(
        ["systemctl", "is-active", "systemd-networkd.service"]
    ).returncode == 0:
        raise ValueError("systemd-networkd is active. Configure NetworkManager yourself before installing this rice")
    if "hardware" in groups and run(["systemctl", "is-active", "tlp.service"]).returncode == 0:
        raise ValueError("TLP is active; omit hardware or resolve its power-profiles-daemon conflict first")
    confirmation = ("Install listed dependencies/services and apply this update, keeping local edits? [y/N] "
                    if update_plans is not None else
                    "Install these packages, enable listed services and back up/replace configs? [y/N] ")
    if not args.yes and input(confirmation).lower() != "y":
        print("Cancelled; no changes made.")
        return 0
    terminal.heading("4 / Install selected packages")
    install_packages(dependencies)
    unresolved = [c for d in dependencies for c in d["commands"] if not shutil.which(c)]
    errors = compatibility() + source_compatibility(REPO)
    if unresolved or errors:
        raise ValueError("Preflight failed; configs untouched: " + "; ".join(errors + unresolved))
    for command in service_commands:
        subprocess.run(command, check=True)
    terminal.heading("5 / Back up and copy configuration")
    conflicts = 0
    if update_plans is not None:
        conflicts = deploy.update(update_plans, groups=groups)
    else:
        deploy.install(groups=groups)
    if args.wallpapers:
        terminal.heading("6 / Optional wallpaper collection")
        deploy.download_wallpapers()
    terminal.heading("Done")
    print(f"{'Updated' if update_plans is not None else 'Installed'}. Log out and enter Hyprland to activate. No shell was launched or reloaded.")
    if conflicts:
        print(f"Kept {conflicts} local conflict(s). Review the incoming copies printed above; rerun update after resolving them.")
    print("Restore configs: ./install.sh restore (packages/services remain installed).")
    return 2 if conflicts else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.SubprocessError, EOFError, KeyboardInterrupt) as error:
        print(f"Installer: {error}", file=sys.stderr)
        sys.exit(1)
