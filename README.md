# Wi-Fi occupancy

Run the terminal chooser with Python 3.10+ and `tshark` on your PATH.

```sh
python3 src/analyze.py
```

Put saved Wi-Fi `.pcap` or `.pcapng` files directly in this checkout's `data/`
directory. Pick a file by number, enter `a` to show a table with one row per
capture, or enter `q` to quit. The results show the unique probe MAC count
and the baseline device estimate for each capture. In the table, `-` marks
the pending OPTICS device estimate.

The included recordings come from [projekt-SCS](https://github.com/Natalaa212/projekt-SCS/tree/6a325f2e26929588b17e6b91eda0866e903fac6d).
Filenames starting with `corridor_` come from `dane_korytarz`, and filenames
starting with `flat_` come from `dane_mieszkanie`.

The [baseline method](docs/README.md#baseline-device-estimate) uses probe
capabilities, timing, and signal strength to group likely address changes.
It estimates the number of Wi-Fi devices observed over the whole recording.
A people count needs separate calibration against known headcounts.

Keep new raw capture files local. Git ignores untracked `.pcap` and `.pcapng` files in
`data/`.
