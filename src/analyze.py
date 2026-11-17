"""Choose Wi-Fi captures and run the probe-source count."""

import sys
from pathlib import Path

from capture import DATA_DIR, list_captures
from counting import count_probe_sources


def choose_captures() -> list[Path]:
    captures = list_captures(DATA_DIR)
    print(f"Wi-Fi captures in {DATA_DIR}")
    for number, path in enumerate(captures, start=1):
        print(f"  {number}. {path.name}")
    if captures:
        print("  a. Analyze all captures")
    else:
        print("  No saved captures. Add a .pcap or .pcapng file here.")
    print("  q. Quit")

    while True:
        choice = input("Selection: ").strip().lower()
        if choice == "q":
            return []
        if choice == "a" and captures:
            return captures

        try:
            number = int(choice)
            if 1 <= number <= len(captures):
                return [captures[number - 1]]
        except ValueError:
            pass
        print("Choose a listed number, a, or q." if captures else "Enter q to quit.")


def main() -> int:
    exit_code = 0
    try:
        for path in choose_captures():
            try:
                count = count_probe_sources(path)
            except (OSError, RuntimeError) as error:
                print(f"Analyze {path.name}: {error}", file=sys.stderr)
                exit_code = 1
            else:
                print(f"{path.name}: {count} unique probe-request source addresses")
    except EOFError:
        print()
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    except (OSError, RuntimeError) as error:
        print(f"Analyze: {error}", file=sys.stderr)
        return 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
