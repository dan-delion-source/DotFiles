# Installer

See the root [README](../README.md) for prerequisites, optional groups,
installation, restoration, and validation limits.

- `../install.sh check`: read-only dependency and compatibility audit.
- `../install.sh install --dry-run`: preview without changing files or packages.
- `../install.sh install`: choose optional groups, review the changes and confirm.
- `../install.sh restore`: recover originals, preserving later configuration edits.

`dependencies.json` is the package/command inventory. `installer.py` resolves
installed and repository providers before using verified AUR candidates. It
validates versions, installed QML modules and QML parsing without starting a shell.
It uses copies rather than links, records content fingerprints, and keeps original
backups across repeated installations. Tests use temporary directories.
