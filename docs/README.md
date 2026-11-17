# Research papers

- **Simončič et al. (2023)** introduce a method for estimating the number of Wi-Fi devices from probe requests. It groups probes sent under different MAC addresses using information elements, arrival times, and signal strength, then uses OPTICS clustering to estimate a device count. The paper evaluates the method on labeled and field captures. [Paper](https://doi.org/10.3390/s23052588)
- **Ficara et al. (2024)** survey Wi-Fi privacy and randomized and changing MAC addresses. The tutorial explains how address rotation affects device counting and reviews passive methods that use frame contents, timing, sequence numbers, and signal strength. [Paper](https://doi.org/10.1109/COMST.2023.3345746)

The local PDF copies are ignored by Git.

## Baseline device estimate

Ficara et al. explain how rotating MAC addresses can inflate a raw address
count. The baseline adapts three signals from Simončič et al. (§4.3.2):
probe-request information elements, arrival time, and received signal strength.

TShark extracts the fields from saved captures. Python records the first and
last probe from each source MAC address. It links two locally administered
unicast addresses when all of the following hold:

- The first probe from the new address occurs within 15 seconds after the last
  probe from the old address.
- Those two probes share the same channel and the same fingerprint of supported
  rates, HT capabilities, VHT receive MCS map, and information element IDs.
- The first antenna's signal readings differ by at most 5 dB.
- Each address has only one candidate for that transition. Ambiguous matches
  and addresses with missing required fields are kept separate.

Each linked chain counts as one estimated device in that capture. The time and
signal thresholds are initial heuristics. Similar devices can look alike, and
a device may keep multiple addresses if its probes differ between them.
Devices that send no probes are absent. The bundled recordings have no
headcount labels for calibrating or evaluating a people estimate.

## OPTICS device estimate

The analyzer groups each address's probes by their information elements and
keeps the timestamps, signal readings, and distinct directed SSIDs. Appendix B
of Simončič et al. describes the distance between profiles. It compares
supported rates, capability bits, vendor and extension tags, shared SSIDs,
and the closest combination of timestamps and signal readings. A missing RSSI
contributes no signal penalty. Profiles with no shared information element
cannot support a match. The address distance averages the closest third of
profile pairs, rounding the number of pairs up.

Following §4.3.2, scikit-learn's OPTICS processes the distances separately for
each local prefix recognized by TShark and for the remaining randomized
addresses. The analyzer extracts clusters from the reachability order using
the rise and drop rules in Appendix B. Each unclustered address remains a
singleton candidate.

Following §4.3.3, a global address and a randomized cluster count as one device
if each is the other's closest candidate, their distance is below 200, and each
runner-up is more than 1.25 times as far away. A candidate with no runner-up
passes the margin check. The distance weights and thresholds come from the
[authors' reference implementation](https://gitlab.com/e62Lab/resiloc_project/wireless-data-analysis/-/blob/main/mac_de_anony.py).
