# Wi-Fi occupancy

## Setup

The analyzer uses uv to manage Python 3.10+ and its project environment.
TShark is installed separately and must be on your PATH.

**macOS with [Homebrew](https://brew.sh/)** — from the repository root:

```sh
brew bundle install --no-upgrade
```

**Debian or Ubuntu**

Run `sudo apt update` and check `apt-cache policy uv`. If APT lists an install
candidate for uv, install both tools together:

```sh
sudo apt install uv tshark
```

If your release has no uv package, use the
[official uv installer](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer)
and follow its PATH instructions:

```sh
sudo apt install curl tshark
curl -LsSf https://astral.sh/uv/install.sh | sh
```

If the installer asks whether non-root users should be allowed to capture
packets, select **No**. The analyzer reads saved captures.

## Run

From the repository root:

```sh
uv run python src/analyze.py
```

Put saved Wi-Fi `.pcap` or `.pcapng` files directly in this checkout's `data/`
directory. Pick a file by number, enter `a` to show a table with one row per
capture, or enter `q` to quit. The results show the unique probe MAC count
and both the baseline and OPTICS device estimates for each capture.

The included recordings come from [projekt-SCS](https://github.com/Natalaa212/projekt-SCS/tree/6a325f2e26929588b17e6b91eda0866e903fac6d).
Filenames starting with `corridor_` come from `dane_korytarz`, and filenames
starting with `flat_` come from `dane_mieszkanie`.

The [baseline method](docs/README.md#baseline-device-estimate) and the
[OPTICS method](docs/README.md#optics-device-estimate) use probe capabilities,
timing, and signal strength to estimate the number of Wi-Fi devices observed
over the whole recording.
A people count needs separate calibration against known headcounts.

Keep new raw capture files local. Git ignores untracked `.pcap` and `.pcapng` files in
`data/`.

## Python dependencies

`uv run` syncs the environment from `uv.lock`. To add a Python library, run
`uv add <package>` and commit the changes to both `pyproject.toml` and `uv.lock`.
