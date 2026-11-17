"""Choose a Wi-Fi capture and run the probe-source count."""

import sys
from pathlib import Path

from capture import DATA_DIR, list_captures, record_capture
from counting import count_probe_sources


def choose_capture() -> Path | None:
    captures = list_captures(DATA_DIR)
    print(f"Wi-Fi captures in {DATA_DIR}")
    for number, path in enumerate(captures, start=1):
        print(f"  {number}. {path.name}")
    if not captures:
        print("  No saved captures. Add a .pcap or .pcapng file here or record one.")
    print("  c. Record a new capture")
    print("  q. Quit")

    while True:
        choice = input("Choose a capture: ").strip().lower()
        if choice == "q":
            return None
        if choice == "c":
            interface = input("Wi-Fi interface (press Enter to cancel): ").strip()
            if not interface:
                continue
            while True:
                duration = input("Recording time in seconds [15]: ").strip() or "15"
                try:
                    seconds = int(duration)
                    if seconds > 0:
                        break
                except ValueError:
                    pass
                print("Enter a positive whole number of seconds.")
            print(f"Recording probe requests for {seconds} seconds...", flush=True)
            path = record_capture(DATA_DIR, interface, seconds)
            print(f"Saved {path.name}.")
            return path

        try:
            number = int(choice)
            if 1 <= number <= len(captures):
                return captures[number - 1]
        except ValueError:
            pass
        print("Choose a listed number, c, or q.")


def main() -> int:
    try:
        path = choose_capture()
        if path is not None:
            count = count_probe_sources(path)
            print(f"{path.name}: {count} unique probe-request source addresses")
    except EOFError:
        print()
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    except (OSError, RuntimeError) as error:
        print(f"Analyze: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
