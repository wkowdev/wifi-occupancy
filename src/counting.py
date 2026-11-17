"""Estimate the number of Wi-Fi devices observed in a saved capture."""

import csv
import subprocess
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryFile

PROBE_FIELDS = (
    "wlan.sa",
    "frame.time_epoch",
    "radiotap.channel.freq",
    "radiotap.dbm_antsignal",
    "wlan.supported_rates",
    "wlan.extended_supported_rates",
    "wlan.ht.capabilities",
    "wlan.vht.mcsset.rxmcsmap",
    "wlan.tag.number",
    "wlan.ext_tag.number",
)

# Starting values for the baseline heuristic. See docs/README.md.
MAX_ADDRESS_GAP_SECONDS = 15
MAX_SIGNAL_DIFFERENCE_DB = 5


@dataclass(frozen=True)
class CaptureCounts:
    unique_probe_macs: int
    baseline_devices: int


@dataclass(frozen=True)
class Probe:
    time: float
    frequency: str
    signal: int | None
    fingerprint: tuple[str, ...]


@dataclass
class AddressSpan:
    first: Probe
    last: Probe


def read_probe_spans(capture_path: Path) -> dict[str, AddressSpan]:
    command = [
        "tshark", "-n", "-r", str(capture_path),
        "-Y", "wlan.fc.type_subtype == 0x04",
        "-T", "fields", "-E", "occurrence=a",
    ]
    for field in PROBE_FIELDS:
        command.extend(("-e", field))

    spans: dict[str, AddressSpan] = {}
    with TemporaryFile(mode="w+t") as errors:
        try:
            decoder = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=errors, text=True, errors="replace"
            )
        except FileNotFoundError as error:
            raise RuntimeError("TShark is required. Install it and add tshark to your PATH.") from error

        with decoder:
            probes = csv.reader(decoder.stdout, delimiter="\t", quoting=csv.QUOTE_NONE)
            for address, time, frequency, signals, *fingerprint in probes:
                if not address:
                    continue
                # Some frames report multiple antennas. Compare the first reading.
                signal = signals.partition(",")[0]
                probe = Probe(float(time), frequency, int(signal) if signal else None,
                              tuple(fingerprint))
                span = spans.get(address)
                if span is None:
                    spans[address] = AddressSpan(probe, probe)
                else:
                    if probe.time < span.first.time:
                        span.first = probe
                    if probe.time > span.last.time:
                        span.last = probe

            if decoder.wait():
                errors.seek(0)
                raise RuntimeError(errors.read().strip() or "TShark could not read the capture.")
    return spans


def probes_match(earlier: Probe, later: Probe) -> bool:
    return (
        bool(earlier.frequency)
        and earlier.frequency == later.frequency
        and bool(earlier.fingerprint[0])  # Supported rates must be present.
        and earlier.fingerprint == later.fingerprint
        and earlier.signal is not None
        and later.signal is not None
        and abs(earlier.signal - later.signal) <= MAX_SIGNAL_DIFFERENCE_DB
    )


def estimate_devices(spans: dict[str, AddressSpan]) -> int:
    # Locally administered unicast addresses may be rotated by the device.
    local_spans = sorted(
        (span for address, span in spans.items() if int(address[:2], 16) & 0x03 == 0x02),
        key=lambda span: span.first.time,
    )
    start_times = [span.first.time for span in local_spans]
    incoming: Counter[int] = Counter()
    unique_successors: list[int] = []
    for span in local_spans:
        first_candidate = bisect_right(start_times, span.last.time)
        end = bisect_right(start_times, span.last.time + MAX_ADDRESS_GAP_SECONDS)
        matches = [
            index for index in range(first_candidate, end)
            if probes_match(span.last, local_spans[index].first)
        ]
        incoming.update(matches)
        if len(matches) == 1:
            unique_successors.append(matches[0])

    # Keep only one-to-one links. As all links go forward in time, each
    # accepted link joins two previously separate address chains.
    links = sum(incoming[index] == 1 for index in unique_successors)
    return len(spans) - links


def count_capture(capture_path: Path) -> CaptureCounts:
    spans = read_probe_spans(capture_path)
    return CaptureCounts(len(spans), estimate_devices(spans))
