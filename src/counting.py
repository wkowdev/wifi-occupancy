"""Estimate the number of Wi-Fi devices observed in a saved capture."""

import json
import subprocess
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryFile

from optics_counting import AddressProbes, estimate_optics_devices

BASELINE_IE_FIELDS = (
    "wlan_wlan_supported_rates",
    "wlan_wlan_extended_supported_rates",
    "wlan_wlan_ht_capabilities",
    "wlan_wlan_vht_mcsset_rxmcsmap",
    "wlan_wlan_tag_number",
    "wlan_wlan_ext_tag_number",
)

# Starting values for the baseline heuristic. See docs/README.md.
MAX_ADDRESS_GAP_SECONDS = 15
MAX_SIGNAL_DIFFERENCE_DB = 5


@dataclass(frozen=True)
class CaptureCounts:
    unique_probe_macs: int
    baseline_devices: int
    optics_devices: int


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


def field_values(layer: dict, name: str) -> list[str]:
    value = layer.get(name, [])
    return value if isinstance(value, list) else [value]


def epoch_seconds(value: str) -> float:
    if not value.endswith("Z"):
        return float(value)
    # EK formats absolute times as UTC ISO 8601 with up to nanosecond precision.
    seconds, _, fraction = value[:-1].partition(".")
    return datetime.fromisoformat(seconds + "+00:00").timestamp() + float("0." + fraction)


def frequency_band(frequency: str) -> int | None:
    """Return the band in GHz (2, 5, or 6) of a channel frequency in MHz."""
    if not frequency:
        return None
    megahertz = int(frequency.split(",")[0])
    return 2 if megahertz < 3000 else 5 if megahertz < 5925 else 6


def read_probe_spans(
    capture_path: Path,
    optics_probes: dict[str, AddressProbes] | None = None,
    spans: dict[str, AddressSpan] | None = None,
) -> dict[str, AddressSpan]:
    """Read probe requests, adding them to `spans` and `optics_probes` when given."""
    command = [
        "tshark", "-n", "-r", str(capture_path),
        "-Y", "wlan.fc.type_subtype == 0x04",
        "-T", "ek", "-x", "-J", "frame radiotap wlan wlan.mgt wlan_radio",
    ]

    if spans is None:
        spans = {}
    with TemporaryFile(mode="w+t") as errors:
        try:
            decoder = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=errors, text=True, errors="replace"
            )
        except FileNotFoundError as error:
            raise RuntimeError("TShark was not found on PATH. See README.md for setup.") from error

        with decoder:
            for line in decoder.stdout:
                layers = json.loads(line).get("layers")
                if not layers:  # EK also emits an index line for each packet.
                    continue
                wlan = layers.get("wlan", {})
                addresses = field_values(wlan, "wlan_wlan_sa")
                if not addresses:
                    continue
                address = addresses[0]
                timestamp = epoch_seconds(layers["frame"]["frame_frame_time_epoch"])
                management = layers.get("wlan_wlan_mgt", {})
                radiotap = layers.get("radiotap", {})
                frequency = ",".join(field_values(radiotap, "radiotap_radiotap_channel_freq"))
                # Some frames report multiple antennas. Compare the first reading.
                signals = field_values(radiotap, "radiotap_radiotap_dbm_antsignal")
                rssi = int(signals[0]) if signals else None
                fingerprint = tuple(",".join(field_values(management, name))
                                    for name in BASELINE_IE_FIELDS)
                if optics_probes is not None:
                    data = optics_probes.get(address)
                    if data is None:
                        vendor = wlan.get("wlan_wlan_sa_oui_resolved")
                        data = AddressProbes(cid=address[:8] if vendor else None)
                        optics_probes[address] = data
                    radio = layers.get("wlan_radio", {})
                    radio_signals = field_values(radio, "wlan_radio_wlan_radio_signal_dbm")
                    optics_rssi = int(radio_signals[0]) if rssi is None and radio_signals else rssi
                    data.add(field_values(management, "wlan_wlan_tag_raw"), timestamp, optics_rssi,
                             frequency_band(frequency))

                probe = Probe(timestamp, frequency, rssi, fingerprint)
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


def count_captures(capture_paths: list[Path]) -> CaptureCounts:
    """Count devices over one or more captures recorded as a single session."""
    optics_probes: dict[str, AddressProbes] = {}
    spans: dict[str, AddressSpan] = {}
    for capture_path in capture_paths:
        read_probe_spans(capture_path, optics_probes, spans)
    return CaptureCounts(len(spans), estimate_devices(spans),
                         estimate_optics_devices(optics_probes))
