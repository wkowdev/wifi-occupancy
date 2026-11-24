"""Choose Wi-Fi captures and show device counts."""

import sys
from pathlib import Path

from capture import DATA_DIR, list_captures
from counting import CaptureCounts, count_captures

SINGLE, TABLE, SESSION = "single", "table", "session"


def parse_numbers(choice: str, count: int) -> list[int] | None:
    """Parse numbers and ranges such as "3", "3-6", or "3,5-6"."""
    numbers = set()
    for part in choice.split(","):
        first, dash, last = part.strip().partition("-")
        try:
            start = int(first)
            end = int(last) if dash else start
        except ValueError:
            return None
        if not 1 <= start <= end <= count:
            return None
        numbers.update(range(start, end + 1))
    return sorted(numbers)


def choose_captures() -> tuple[list[Path], str]:
    captures = list_captures(DATA_DIR)
    print(f"Wi-Fi captures in {DATA_DIR}")
    for number, path in enumerate(captures, start=1):
        print(f"  {number}. {path.name}")
    if captures:
        print("  a. Analyze all captures as a table")
    else:
        print("  No saved captures. Add a .pcap or .pcapng file here.")
    if len(captures) > 1:
        print("  Enter several numbers, such as 3-6 or 3,5, to analyze them as one session.")
    print("  q. Quit")

    while True:
        choice = input("Selection: ").strip().lower()
        if choice == "q":
            return [], SINGLE
        if choice == "a" and captures:
            return captures, TABLE

        numbers = parse_numbers(choice, len(captures))
        if numbers:
            selected = [captures[number - 1] for number in numbers]
            return selected, SINGLE if len(selected) == 1 else SESSION
        print("Choose listed numbers, a, or q." if captures else "Enter q to quit.")


def describe(counts: CaptureCounts) -> str:
    return (f"{counts.unique_probe_macs} unique probe-request source addresses, "
            f"{counts.baseline_devices} estimated devices (baseline), "
            f"{counts.optics_devices} estimated devices (OPTICS)")


def print_results_table(results: list[tuple[str, str, str, str]]) -> None:
    rows = [
        ("Capture", "Unique probe MACs", "Baseline device estimate", "OPTICS device estimate"),
        *results,
    ]
    widths = [max(map(len, column)) for column in zip(*rows)]
    for row in rows:
        print(" | ".join(value.ljust(width) for value, width in zip(row, widths)).rstrip())


def main() -> int:
    exit_code = 0
    try:
        captures, mode = choose_captures()
        if mode == SESSION:
            names = ", ".join(path.name for path in captures)
            try:
                counts = count_captures(captures)
            except (OSError, RuntimeError) as error:
                print(f"Analyze session ({names}): {error}", file=sys.stderr)
                return 1
            print(f"Session of {len(captures)} captures ({names}): {describe(counts)}")
            return 0

        results = []
        for path in captures:
            try:
                counts = count_captures([path])
            except (OSError, RuntimeError) as error:
                print(f"Analyze {path.name}: {error}", file=sys.stderr)
                exit_code = 1
                if mode == TABLE:
                    results.append((path.name, "error", "error", "error"))
            else:
                if mode == TABLE:
                    results.append((path.name, str(counts.unique_probe_macs),
                                    str(counts.baseline_devices), str(counts.optics_devices)))
                else:
                    print(f"{path.name}: {describe(counts)}")
        if mode == TABLE:
            print()
            print_results_table(results)
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
