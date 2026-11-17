# Wi-Fi occupancy

Run the terminal chooser with Python 3.10+ and `tcpdump` on your PATH.

```sh
python3 src/analyze.py
```

Put saved Wi-Fi `.pcap` or `.pcapng` files directly in this checkout's `data/`
directory. Pick a file by number, enter `a` to show a table with one row per
capture, or enter `q` to quit. The table shows the filename and count, with `-`
as the placeholder for each algorithm.

The included recordings come from [projekt-SCS](https://github.com/Natalaa212/projekt-SCS/tree/6a325f2e26929588b17e6b91eda0866e903fac6d).
Filenames starting with `corridor_` come from `dane_korytarz`, and filenames
starting with `flat_` come from `dane_mieszkanie`.

The result is the number of unique source MAC addresses in Wi-Fi probe requests.
MAC randomization can make one device appear under multiple addresses, and
devices that send no probe request during the capture are absent from the count.
Keep new raw capture files local. Git ignores untracked `.pcap` and `.pcapng` files in
`data/`.
