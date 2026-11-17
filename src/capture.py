"""Locate saved Wi-Fi captures."""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def list_captures(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        return []
    return sorted(
        (
            path for path in data_dir.iterdir()
            if not path.name.startswith(".")
            and path.suffix.lower() in {".pcap", ".pcapng"}
            and path.is_file()
        ),
        key=lambda path: (path.name.casefold(), path.name),
    )
