#!/usr/bin/env python3
"""Shared Fastfetch logo discovery, selection and terminal rendering."""
import json
import os
import re
import subprocess
import sys

REMOVED_SCENES = frozenset({"lava", "critters", "koi", "invaders", "random"})
DEFAULT_CHOICE = "cat"
EXTRA_LOGOS = {"arch": ("file", "arch.txt"), "cat": ("kitty-icat", "cat.gif")}
CHOICES = tuple(EXTRA_LOGOS)

STATE_DIR = os.path.join(os.environ.get("XDG_STATE_HOME")
                         or os.path.expanduser("~/.local/state"), "danshell")
CHOICE_FILE = os.path.join(STATE_DIR, "greeting")
LINK = os.path.join(STATE_DIR, "greeting.gif")
FASTFETCH_CONFIG = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             "../../fastfetch/config.jsonc"))
LOGO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                       "../../fastfetch/logos"))
LOGO_EXTENSIONS = (".txt", ".png", ".jpg", ".jpeg", ".webp", ".gif")


def file_choice(filename):
    for choice, (_, supplied) in EXTRA_LOGOS.items():
        if filename == supplied:
            return choice
    return "logo:" + filename


def list_greetings():
    entries = []
    if not os.path.isdir(LOGO_DIR):
        return entries
    for filename in sorted(os.listdir(LOGO_DIR), key=str.casefold):
        source = os.path.join(LOGO_DIR, filename)
        if (filename.startswith(".") or not filename.lower().endswith(LOGO_EXTENSIONS)
                or not os.path.isfile(source)):
            continue
        status = os.stat(source)
        entries.append({"id": file_choice(filename),
                        "label": os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title(),
                        "kind": "text" if filename.lower().endswith(".txt") else "image",
                        "path": source,
                        "version": f"{status.st_mtime_ns}-{status.st_size}"})
    return entries


def external_source(choice):
    if choice in EXTRA_LOGOS:
        return os.path.join(LOGO_DIR, EXTRA_LOGOS[choice][1])
    if choice.startswith("logo:"):
        filename = choice[5:]
        if (filename and filename == os.path.basename(filename)
                and not filename.startswith(".")
                and filename.lower().endswith(LOGO_EXTENSIONS)):
            return os.path.join(LOGO_DIR, filename)
    return None



def replace_text(path, text):
    staging = f"{path}.{os.getpid()}.part"
    with open(staging, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(staging, path)


def read_choice():
    try:
        with open(CHOICE_FILE, encoding="utf-8") as handle:
            choice = handle.read().strip()
        return choice if choice in CHOICES or external_source(choice) else DEFAULT_CHOICE
    except OSError:
        return DEFAULT_CHOICE



def logo_source(choice):
    """Resolve a supplied logo together with its Fastfetch renderer."""
    source = external_source(choice)
    if not source:
        raise ValueError(f"Unknown greeting: {choice}")
    if not os.path.isfile(source):
        raise ValueError(f"Fastfetch logo is missing: {source}")
    return ("file" if source.lower().endswith(".txt") else "kitty-icat"), source

def show(arguments):
    """Run Fastfetch without confusing a scene file with the saved logo type.

    An explicit choice only affects this invocation; the Settings selection
    and the Fastfetch config remain unchanged.
    """
    arguments = list(arguments)
    choice = arguments.pop(0) if arguments and not arguments[0].startswith("-") else read_choice()
    try:
        logo_type, source = logo_source(choice)
        return subprocess.call(["fastfetch", "--config", FASTFETCH_CONFIG,
                                "--logo-type", logo_type, "--logo", source, *arguments])
    except (OSError, ValueError) as error:
        sys.stderr.write(f"Cannot show Fastfetch greeting: {error}\n")
        return 1


def choose(choice):
    """Save the logo choice without changing Fastfetch modules."""
    try:
        logo_type, resolved = logo_source(choice)
    except ValueError as error:
        sys.stderr.write(f"{error}\n")
        return False
    source = resolved
    # Only the logo block changes; all the user's Fastfetch modules stay as-is.
    # The installer links this config into ~/.config/fastfetch when installed.
    try:
        with open(FASTFETCH_CONFIG, encoding="utf-8") as handle:
            config = handle.read()
        pattern = r'("logo"\s*:\s*\{[^}]*?"type"\s*:\s*")[^"]+("[^}]*?"source"\s*:\s*")(?:\\.|[^"\\])*("[^}]*?"width")'
        updated, count = re.subn(pattern, lambda match: match.group(1) + logo_type +
                                 match.group(2) + json.dumps(source, ensure_ascii=False)[1:-1] + match.group(3), config, count=1,
                                 flags=re.DOTALL)
        if count != 1:
            raise ValueError("Fastfetch logo block not found")
        if updated != config:
            replace_text(FASTFETCH_CONFIG, updated)
    except (OSError, ValueError) as error:
        sys.stderr.write(f"Cannot update Fastfetch logo: {error}\n")
        return False
    os.makedirs(STATE_DIR, exist_ok=True)
    replace_text(CHOICE_FILE, choice + "\n")
    return True



def seed():
    """Select the default on first use or when a removed scene was saved."""
    try:
        with open(CHOICE_FILE, encoding="utf-8") as handle:
            saved = handle.read().strip()
    except OSError:
        saved = None
    if saved is None or saved in REMOVED_SCENES:
        return choose(DEFAULT_CHOICE)
    return True


USAGE = "greeting.py list | choose <id from list> | seed | show [choice] [fastfetch options]"

if __name__ == "__main__":
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    if verb == "list" and len(sys.argv) == 2:
        try:
            print(json.dumps(list_greetings()))
        except OSError as error:
            sys.stderr.write(f"Cannot scan Fastfetch logos: {error}\n")
            sys.exit(1)
        sys.exit(0)
    if verb == "choose" and len(sys.argv) == 3:
        sys.exit(0 if choose(sys.argv[2]) else 1)
    if verb == "seed" and len(sys.argv) == 2:
        sys.exit(0 if seed() else 1)
    if verb == "show":
        sys.exit(show(sys.argv[2:]))
    sys.stderr.write(f"Usage: {USAGE}\n")
    sys.exit(1)
