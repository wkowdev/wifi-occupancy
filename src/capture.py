"""Locate saved Wi-Fi captures and record new probe requests."""

import signal
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROBE_REQUEST_FILTER = "type mgt subtype probe-req"


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


def record_capture(data_dir: Path, interface: str, seconds: int) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        dir=data_dir, prefix="wifi-", suffix=".tmp", delete=False
    ) as output:
        temporary_path = Path(output.name)
        try:
            with subprocess.Popen(
                ["tcpdump", "-I", "-i", interface, "-w", "-", PROBE_REQUEST_FILTER],
                stdout=output,
            ) as capture:
                try:
                    status = capture.wait(timeout=seconds)
                except subprocess.TimeoutExpired:
                    capture.send_signal(signal.SIGINT)
                    status = capture.wait()
            if status:
                raise RuntimeError(f"tcpdump capture failed (exit status {status}).")
            output.close()
            return temporary_path.rename(temporary_path.with_suffix(".pcap"))
        finally:
            temporary_path.unlink(missing_ok=True)
