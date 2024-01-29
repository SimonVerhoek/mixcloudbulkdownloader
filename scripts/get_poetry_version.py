import os
import tomllib
from pathlib import Path


ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_poetry_version(root_dir: Path = ROOT_DIR) -> str:
    """Reads version from poetry config file."""
    with open(root_dir / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
        return data["tool"]["poetry"]["version"]


if __name__ == "__main__":
    print(get_poetry_version())
