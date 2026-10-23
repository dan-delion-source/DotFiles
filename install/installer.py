#!/usr/bin/env python3
"""Auditable, backup-first installer for an existing Arch Hyprland desktop."""
import argparse
import contextlib
import fcntl
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


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


class Deployment:
    def __init__(self, repo, config, data, state):
        self.repo = repo.resolve()
        self.config, self.data, self.state = [p.absolute() for p in (config, data, state)]
        self.directory = self.state / "danshell-installer"
        self.record = self.directory / "installation.json"
        self.targets = [(self.repo / "config" / name, self.config / name)
                        for name in ("hypr", "quickshell", "kitty", "fastfetch", "matugen")]
        self.targets.append((self.repo / "Wallpapers", self.data / "wallpapers"))
        destinations = [destination for _, destination in self.targets]
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
        allowed = {str(d) for _, d in self.targets}
        for entry in document["entries"]:
            if entry["destination"] not in allowed:
                raise ValueError("Installation uses different XDG directories; use the original paths")
            if entry.get("backup") and not Path(entry["backup"]).is_relative_to(self.directory):
                raise ValueError("Invalid backup path in installation record")
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
            if not source.is_dir():
                raise ValueError(f"Missing source: {source}")
            entry = entries.get(str(destination))
            if entry and (entry.get("pending") or fingerprint(destination) != entry["installed"]):
                raise ValueError(f"Changed since installation: {destination}. Restore first; edits will be preserved.")

    def install(self):
        with self.locked():
            document = self.load()
            entries = {e["destination"]: e for e in document["entries"]}
            self.preflight(document)
            batch = str(time.time_ns())
            for index, (source, destination) in enumerate(self.targets):
                wanted = fingerprint(source)
                entry = entries.get(str(destination))
                if entry and wanted == entry["installed"]:
                    print(f"UNCHANGED {destination}")
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                stage = Path(tempfile.mkdtemp(prefix=".danshell-", dir=destination.parent))
                staged = stage / "config"
                try:
                    copy(source, staged)
                    if entry is None:
                        backup = self.directory / "backups" / batch / str(index)
                        backup.parent.mkdir(parents=True, exist_ok=True)
                        original = exists(destination)
                        entry = {"destination": str(destination), "backup": str(backup) if original else None,
                                 "installed": wanted, "pending": True}
                        if original:
                            # Copy first so a crash cannot lose the original.
                            copy(destination, backup)
                        document["entries"].append(entry)
                        save(self.record, document)
                    else:
                        entry["pending"] = True
                        save(self.record, document)
                    remove(destination)
                    staged.replace(destination)
                    entry.update(installed=wanted, pending=False)
                    save(self.record, document)
                    print(f"INSTALLED {destination}")
                finally:
                    remove(stage)

    def restore(self, dry_run=False):
        if not self.record.exists():
            print("No installation record; nothing to restore.")
            return
        if dry_run:
            for entry in reversed(self.load()["entries"]):
                print(f"RESTORE {entry['destination']} (preserve changes if present)")
            return
        with self.locked():
            document = self.load()
            for entry in reversed(document["entries"][:]):
                destination = Path(entry["destination"])
                backup = Path(entry["backup"]) if entry["backup"] else None
                if backup and not exists(backup):
                    raise ValueError(f"Backup missing: {backup}; leaving {destination} untouched")
                changed = fingerprint(destination) != entry["installed"] or entry.get("pending")
                if exists(destination) and changed:
                    preserved = self.directory / "preserved" / str(time.time_ns()) / destination.name
                    preserved.parent.mkdir(parents=True, exist_ok=True)
                    copy(destination, preserved)
                    print(f"PRESERVED edits: {preserved}")
                remove(destination)
                if backup:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    copy(backup, destination)
                document["entries"].remove(entry)
                save(self.record, document)
                print(f"RESTORED {destination}")
            self.record.unlink()


def selection(manifest, names):
    chosen = {"core"} | {n for name in names for n in name.split(",") if n}
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
        raise ValueError("Supported target: an existing CachyOS/Arch Hyprland desktop")
    if not shutil.which("pacman"):
        raise ValueError("pacman is required")


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("command", choices=("check", "install", "restore"))
    cli.add_argument("--groups", action="append", default=[], help="Comma-separated optional feature groups")
    cli.add_argument("--dry-run", action="store_true", help="Read-only preview; no packages, configs or state are written")
    cli.add_argument("--yes", action="store_true", help="Accept the displayed installer plan; package manager prompts remain")
    cli.add_argument("--config-dir", type=Path, default=Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"))
    cli.add_argument("--data-dir", type=Path, default=Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share"))
    cli.add_argument("--state-dir", type=Path, default=Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state"))
    return cli


def main():
    args = parser().parse_args()
    deploy = Deployment(REPO, args.config_dir, args.data_dir, args.state_dir)
    if args.command == "restore":
        if not args.dry_run and os.geteuid() == 0:
            raise ValueError("Run as your desktop user, without sudo")
        deploy.restore(args.dry_run)
        return 0
    platform_check()
    manifest = json.loads(MANIFEST.read_text())
    if args.command == "install" and not args.groups and not args.yes and not args.dry_run:
        for name, feature in manifest["features"].items():
            if name != "core":
                print(f"  {name}: {feature['description']}")
        args.groups = [input("Optional groups (comma-separated; Enter for core only): ").strip()]
    groups = selection(manifest, args.groups)
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
        if not active:
            action = ["start"] if service.get("activation") == "dbus" else ["enable", "--now"]
            service_commands.append((["sudo"] if service["scope"] == "system" else [])
                                    + command + action + [service["name"]])
    for command in service_commands:
        print("SERVICE ACTION " + " ".join(command))
    errors = compatibility() + qml_compatibility(REPO)
    for error in errors:
        print("COMPATIBILITY " + error)
    deploy.preview()
    deploy.preflight()
    if args.command == "check":
        for error in service_errors:
            print("UNVERIFIED " + error)
        return int(bool(errors or service_commands or any(d["source"] != "installed" or
                   any(not shutil.which(c) for c in d["commands"]) for d in dependencies)))
    if args.dry_run:
        return 0
    if os.geteuid() == 0:
        raise ValueError("Run as your desktop user; sudo is used only for system packages and services")
    if not shutil.which("Hyprland"):
        raise ValueError("An existing Hyprland desktop is required; this installer does not install Hyprland")
    if service_errors:
        raise ValueError("Run installation from the target user's systemd desktop session; service checks failed")
    # Do not replace an existing network manager's live connection.
    if any("NetworkManager.service" in c for c in service_commands) and run(
        ["systemctl", "is-active", "systemd-networkd.service"]
    ).returncode == 0:
        raise ValueError("systemd-networkd is active. Configure NetworkManager yourself before installing this rice")
    if "hardware" in groups and run(["systemctl", "is-active", "tlp.service"]).returncode == 0:
        raise ValueError("TLP is active; omit hardware or resolve its power-profiles-daemon conflict first")
    if not args.yes and input("Install these packages, enable listed services and back up/replace configs? [y/N] ").lower() != "y":
        print("Cancelled; no changes made.")
        return 0
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
    unresolved = [c for d in dependencies for c in d["commands"] if not shutil.which(c)]
    errors = compatibility() + qml_compatibility(REPO)
    if unresolved or errors:
        raise ValueError("Preflight failed; configs untouched: " + "; ".join(errors + unresolved))
    for command in service_commands:
        subprocess.run(command, check=True)
    deploy.install()
    print("Installed. Log out and enter Hyprland to activate. No shell was launched or reloaded.")
    print("Restore configs: ./install.sh restore (packages/services remain installed).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.SubprocessError, EOFError, KeyboardInterrupt) as error:
        print(f"Installer: {error}", file=sys.stderr)
        sys.exit(1)
