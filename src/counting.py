"""Count distinct source addresses in saved Wi-Fi probe requests."""

import re
import subprocess
from pathlib import Path
from tempfile import TemporaryFile

from capture import PROBE_REQUEST_FILTER

SOURCE_ADDRESS = re.compile(r"\bSA:((?:[0-9a-f]{2}:){5}[0-9a-f]{2})\b", re.I)


def count_probe_sources(capture_path: Path) -> int:
    addresses = set()
    command = ["tcpdump", "-ent", "-r", str(capture_path), PROBE_REQUEST_FILTER]
    with TemporaryFile(mode="w+t") as errors, subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=errors, text=True, errors="replace"
    ) as decoder:
        for line in decoder.stdout:
            source = SOURCE_ADDRESS.search(line)
            if source:
                addresses.add(source[1].lower())

        if decoder.wait():
            errors.seek(0)
            raise RuntimeError(errors.read().strip() or "tcpdump could not read the capture.")

    return len(addresses)
