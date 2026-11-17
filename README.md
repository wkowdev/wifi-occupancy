# Wi-Fi occupancy

Run the terminal chooser with Python 3.10+ and `tcpdump` on your PATH.

```sh
python3 src/analyze.py
```

Put saved Wi-Fi `.pcap` or `.pcapng` files directly in this checkout's `data/`
directory and pick a file by number. You can also choose `c` to record probe
requests on a Wi-Fi interface, save the capture to `data/`, and analyze it
immediately. Live recording requires a monitor-mode-capable adapter and packet
capture permissions. Use `tcpdump -D` to list interfaces.

The result is the number of unique source MAC addresses in Wi-Fi probe requests.
MAC randomization can make one device appear under multiple addresses, and
devices that send no probe request during the capture are absent from the count.
Keep raw capture files local. Git ignores the supported capture extensions in
`data/`.
