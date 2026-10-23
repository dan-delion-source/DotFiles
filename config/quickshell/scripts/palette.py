"""Matugen's Material colours adapted to the shell's existing palette API."""
import json
from pathlib import Path
import re
import subprocess


ROLES = {
    "background": "background", "surface": "surface_container",
    "surfaceHover": "surface_container_high", "border": "outline_variant",
    "text": "on_surface", "textMuted": "on_surface_variant",
    "accent": "primary", "accentHover": "on_primary_container",
    "accentText": "on_primary", "red": "error",
    "green": "tertiary", "yellow": "secondary", "blue": "primary",
}


def validate(palette):
    if not isinstance(palette, dict) or any(
        not re.fullmatch(r"#[0-9a-fA-F]{6}", str(palette.get(key, "")))
        for key in ROLES
    ):
        raise ValueError("Matugen returned an incomplete colour palette")
    return {key: palette[key] for key in ROLES}


def from_json(data):
    # Matugen 4: colours.<role>.dark.color. Matugen 3 used a hex field.
    colors = data["colors"]
    def color(role):
        value = colors[role]["dark"]
        return value.get("color", value.get("hex")) if isinstance(value, dict) else value
    return validate({key: color(role) for key, role in ROLES.items()})


def generate(image):
    config = Path(__file__).resolve().parents[2] / "matugen" / "config.toml"
    try:
        result = subprocess.run(
            ["matugen", "image", str(image), "--config", str(config), "--dry-run",
             "--json", "hex", "--mode", "dark", "--type", "scheme-tonal-spot",
             "--source-color-index", "0"],
            capture_output=True, text=True, timeout=45, check=True,
        )
    except subprocess.CalledProcessError as error:
        detail = re.sub(r"\x1b\[[0-9;]*m", "", error.stderr or "").strip()
        raise ValueError(detail[:600] or "Matugen could not generate colours") from error
    try:
        return from_json(json.loads(result.stdout))
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise ValueError("Matugen returned invalid colours; run install.sh check") from error
