# Wi-Fi occupancy

## Setup

The analyzer needs Python 3.10+ and TShark on your PATH. It uses only the Python
standard library, so there are no packages to install with `pip`.

**macOS with [Homebrew](https://brew.sh/)** — from the repository root:

```sh
brew bundle install --no-upgrade
```

**Debian or Ubuntu**:

```sh
sudo apt update
sudo apt install python3 tshark
```

If the installer asks whether non-root users should be allowed to capture
packets, select **No**. The analyzer reads saved captures.

## Run

From the repository root:

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
