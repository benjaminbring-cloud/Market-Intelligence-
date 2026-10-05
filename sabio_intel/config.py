import os
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = Path(os.environ.get("MI_DATA_DIR", ROOT / "data"))
OUTPUT_DIR = Path(os.environ.get("MI_OUTPUT_DIR", ROOT / "output"))
MODEL = os.environ.get("MI_MODEL", "claude-sonnet-5-5")


def load(name: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / f"{name}.yaml").read_text())
