"""Estimate devices with the probe-request method of Simončič et al. (2023)."""

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from math import inf

import numpy as np
from sklearn.cluster import OPTICS

# Algorithm A1, A2, and matching coefficients from the authors' reference code.
STARTING_DISTANCE = 100
MIN_DISTANCE = 88
MAX_DISTANCE = 200
REACHABILITY_RISE = 1.25
REACHABILITY_DROP = 0.85
MATCH_MARGIN = 1.25
RSSI_BASE = 1.055
TIMING_THRESHOLD_SECONDS = 0.1
TIMING_DISCOUNT = 10
# Addresses in one cluster that are active at the same time, beyond this
# margin at each end of their activity, belong to separate devices.
OVERLAP_SLACK_SECONDS = 1.0

SSID = 0
SUPPORTED_RATES = 1
EXTENDED_RATES = 50
VENDOR_SPECIFIC = 221
EXTENSION = 255
# Tag ID: (bit-distance weight, different-length penalty)
CAPABILITY_WEIGHTS = {
    45: (400, None),  # HT capabilities
    107: (500, 50),  # Interworking
    127: (100, 35),  # Extended capabilities
    191: (600, None),  # VHT capabilities
}
DISTANCE_TAGS = {SUPPORTED_RATES, EXTENDED_RATES, VENDOR_SPECIFIC, EXTENSION,
                 *CAPABILITY_WEIGHTS}

# Arrival time, signal strength in dBm, and frequency band in GHz.
Observation = tuple[float, int | None, int | None]
TagProfile = tuple[bytes, ...]


@dataclass
class AddressProbes:
    cid: str | None = None
    profiles: dict[TagProfile, list[Observation]] = field(default_factory=dict)
    ssids: set[bytes] = field(default_factory=set)

    def add(self, raw_tags: list[str], time: float, signal: int | None,
            band: int | None) -> None:
        tags = set()
        for raw_tag in raw_tags:
            tag = bytes.fromhex(raw_tag)
            if len(tag) < 3 or len(tag) != tag[1] + 2:
                continue  # Empty or truncated information element.
            if tag[0] == SSID:
                self.ssids.add(tag[2:])
            elif tag[0] in DISTANCE_TAGS:
                tags.add(tag)
        self.profiles.setdefault(tuple(sorted(tags)), []).append((time, signal, band))

    def merge(self, other: "AddressProbes") -> None:
        self.ssids.update(other.ssids)
        for profile, observations in other.profiles.items():
            self.profiles.setdefault(profile, []).extend(observations)

    def time_span(self) -> tuple[float, float]:
        times = [time for observations in self.profiles.values() for time, _, _ in observations]
        return min(times), max(times)


def split_elements(profile: TagProfile) -> dict:
    elements = {}
    for tag in profile:
        tag_id, payload = tag[0], tag[2:]
        if tag_id in (SUPPORTED_RATES, EXTENDED_RATES):
            elements.setdefault(SUPPORTED_RATES, set()).update(payload)
        elif tag_id == EXTENSION:
            elements.setdefault(tag_id, {})[payload[0]] = payload[1:]
        elif tag_id == VENDOR_SPECIFIC:
            if len(payload) >= 3:
                vendor = elements.setdefault(tag_id, {}).setdefault(payload[:3], {})
                if len(payload) >= 4:
                    vendor[payload[3]] = payload[4:]
        else:
            elements[tag_id] = payload
    return elements


def bit_distance(left: bytes, right: bytes) -> float:
    if left == right:
        return 0
    width = max(len(left), len(right))
    common = min(len(left), len(right))
    differing = sum((a ^ b).bit_count() for a, b in zip(left, right))
    return (differing + 8 * (width - common)) / (8 * width)


def data_id_distance(left: dict[int, bytes], right: dict[int, bytes]) -> float:
    return sum(100 * bit_distance(left[key], right[key]) - 8
               for key in sorted(left.keys() & right.keys()))


def information_distance(left: dict, right: dict) -> float:
    shared = left.keys() & right.keys()
    if not shared:
        return inf
    distance = STARTING_DISTANCE + 15 * len(left.keys() ^ right.keys()) / len(shared)
    for tag_id in sorted(shared):
        a, b = left[tag_id], right[tag_id]
        if tag_id == SUPPORTED_RATES:
            distance += 25 * len(a ^ b)
        elif tag_id == VENDOR_SPECIFIC:
            vendors = a.keys() & b.keys()
            distance += -2.5 + 6 * (len(a.keys() ^ b.keys()) - len(vendors))
            distance += sum(data_id_distance(a[vendor], b[vendor])
                            for vendor in sorted(vendors))
        elif tag_id == EXTENSION:
            distance += -2.5 + 6 * len(a.keys() ^ b.keys()) + data_id_distance(a, b)
        else:
            weight, length_penalty = CAPABILITY_WEIGHTS[tag_id]
            if length_penalty is not None and len(a) != len(b):
                distance += length_penalty
            else:
                distance += weight * bit_distance(a, b)
    return distance


def observation_distance(left: list[Observation], right: list[Observation]) -> float:
    best = inf
    for time_a, signal_a, band_a in left:
        for time_b, signal_b, band_b in right:
            distance = 0.0
            # The receiver reports different signal levels in each band, so
            # only readings from the same band are compared.
            if signal_a is not None and signal_b is not None and band_a == band_b:
                distance = RSSI_BASE ** abs(signal_a - signal_b) - 1
            if abs(time_a - time_b) < TIMING_THRESHOLD_SECONDS:
                distance -= TIMING_DISCOUNT
            if distance == -TIMING_DISCOUNT:
                return distance
            best = min(best, distance)
    return best


def address_distance(left: AddressProbes, right: AddressProbes) -> float:
    """Average the closest third of pairs of distinct IE profiles (§4.3.2)."""
    ssid_discount = 25 * len(left.ssids & right.ssids)
    right_profiles = [(split_elements(tags), observations)
                      for tags, observations in right.profiles.items()]
    distances = []
    for tags, observations in left.profiles.items():
        elements = split_elements(tags)
        for other_elements, other_observations in right_profiles:
            distance = information_distance(elements, other_elements)
            if distance < inf:
                distance += observation_distance(observations, other_observations)
                distance = max(MIN_DISTANCE, distance - ssid_discount)
            distances.append(distance)
    closest_count = (len(distances) + 2) // 3
    return sum(sorted(distances)[:closest_count]) / closest_count


def reachability_labels(reachability: np.ndarray) -> list[int]:
    """Extract valleys from the OPTICS ordering (Appendix B, Algorithm A2)."""
    labels = [-1] * len(reachability)
    cluster = -1
    in_cluster = False
    rise_start = None
    drop_start = None
    for index, (current, next_distance) in enumerate(zip(reachability, reachability[1:])):
        if in_cluster:
            if next_distance > current:
                if rise_start is None:
                    rise_start = current
                if next_distance > MAX_DISTANCE or next_distance > rise_start * REACHABILITY_RISE:
                    in_cluster = False
                    rise_start = None
                    continue
            else:
                rise_start = None
            labels[index + 1] = cluster
        elif next_distance < current:
            if drop_start is None:
                drop_start = index
            if (next_distance < MAX_DISTANCE
                    and next_distance < reachability[drop_start] * REACHABILITY_DROP):
                cluster += 1
                labels[drop_start:index + 2] = [cluster] * (index + 2 - drop_start)
                in_cluster = True
                drop_start = None
        else:
            drop_start = None
    return labels


def concurrent_addresses(addresses: list[AddressProbes]) -> int:
    """Return the most addresses active at once. A device uses one address at a time."""
    changes = []
    for address in addresses:
        start, end = address.time_span()
        start += OVERLAP_SLACK_SECONDS
        end -= OVERLAP_SLACK_SECONDS
        if start < end:
            changes += [(start, 1), (end, -1)]
    active = most = 0
    for _, change in sorted(changes):  # At equal times, an end sorts before a start.
        active += change
        most = max(most, active)
    return max(1, most)


def cluster_random_addresses(addresses: list[AddressProbes]) -> list[tuple[AddressProbes, int]]:
    """Return each candidate with the number of devices it represents."""
    if len(addresses) < 2:
        return [(address, 1) for address in addresses]
    distances = np.zeros((len(addresses), len(addresses)))
    has_neighbors = False
    for first, second in combinations(range(len(addresses)), 2):
        distance = address_distance(addresses[first], addresses[second])
        if distance <= MAX_DISTANCE:
            has_neighbors = True
        # sklearn requires finite inputs. Distances above max_eps are unreachable.
        distances[first, second] = distances[second, first] = min(distance, MAX_DISTANCE + 1)
    if not has_neighbors:
        return [(address, 1) for address in addresses]

    model = OPTICS(min_samples=2, max_eps=MAX_DISTANCE, metric="precomputed").fit(distances)
    labels = reachability_labels(model.reachability_[model.ordering_])
    members: dict[int, list[AddressProbes]] = {}
    singletons = []
    for index, label in zip(model.ordering_, labels):
        if label == -1:
            singletons.append((addresses[index], 1))
        else:
            members.setdefault(label, []).append(addresses[index])

    clusters = []
    for cluster_members in members.values():
        merged = AddressProbes()
        for address in cluster_members:
            merged.merge(address)
        clusters.append((merged, concurrent_addresses(cluster_members)))
    return singletons + clusters


def best_match(distances: np.ndarray) -> int | None:
    best = int(np.argmin(distances))
    distance = distances[best]
    if distance >= MAX_DISTANCE:
        return None
    if len(distances) > 1 and np.partition(distances, 1)[1] <= MATCH_MARGIN * distance:
        return None
    return best


def estimate_optics_devices(probes: dict[str, AddressProbes]) -> int:
    global_addresses = []
    random_groups = defaultdict(list)
    non_unicast_count = 0
    for address, data in sorted(probes.items()):
        flags = int(address[:2], 16) & 0x03
        if flags == 0x02:
            random_groups[data.cid].append(data)
        elif flags == 0x00:
            global_addresses.append(data)
        else:
            non_unicast_count += 1

    candidates = [candidate for group in random_groups.values()
                  for candidate in cluster_random_addresses(group)]
    random_clusters = [cluster for cluster, _ in candidates]
    total = (len(global_addresses) + sum(devices for _, devices in candidates)
             + non_unicast_count)
    if not global_addresses or not random_clusters:
        return total

    # §4.3.3: only global-to-random distances can produce a match.
    distances = np.array([[address_distance(address, cluster) for cluster in random_clusters]
                          for address in global_addresses])
    for index, row in enumerate(distances):
        candidate = best_match(row)
        if candidate is not None and best_match(distances[:, candidate]) == index:
            total -= 1
    return total
