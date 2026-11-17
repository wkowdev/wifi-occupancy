"""Choose a Wi-Fi capture and run the probe-source count."""

import sys
from pathlib import Path

from capture import DATA_DIR, list_captures
from counting import count_probe_sources


def choose_capture() -> Path | None:
    captures = list_captures(DATA_DIR)
    print(f"Wi-Fi captures in {DATA_DIR}")
    for number, path in enumerate(captures, start=1):
        print(f"  {number}. {path.name}")
    if not captures:
        print("  No saved captures. Add a .pcap or .pcapng file here.")
    print("  q. Quit")

    while True:
        choice = input("Selection: ").strip().lower()
        if choice == "q":
            return None

        try:
            number = int(choice)
            if 1 <= number <= len(captures):
                return captures[number - 1]
        except ValueError:
            pass
        print("Choose a listed number or q." if captures else "Enter q to quit.")


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
