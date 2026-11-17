"""Choose Wi-Fi captures and run the probe-source count."""

import sys
from pathlib import Path

from capture import DATA_DIR, list_captures
from counting import count_probe_sources


def choose_captures() -> tuple[list[Path], bool]:
    captures = list_captures(DATA_DIR)
    print(f"Wi-Fi captures in {DATA_DIR}")
    for number, path in enumerate(captures, start=1):
        print(f"  {number}. {path.name}")
    if captures:
        print("  a. Analyze all captures as a table")
    else:
        print("  No saved captures. Add a .pcap or .pcapng file here.")
    print("  q. Quit")

    while True:
        choice = input("Selection: ").strip().lower()
        if choice == "q":
            return [], False
        if choice == "a" and captures:
            return captures, True

        try:
            number = int(choice)
            if 1 <= number <= len(captures):
                return [captures[number - 1]], False
        except ValueError:
            pass
        print("Choose a listed number, a, or q." if captures else "Enter q to quit.")


def print_results_table(results: list[tuple[str, str]]) -> None:
    rows = [
        ("name", "num_of_uniq_probe_req", "placeholder default alg", "placeholder ext alg"),
        *((name, count, "-", "-") for name, count in results),
    ]
    widths = [max(map(len, column)) for column in zip(*rows)]
    for row in rows:
        print(" | ".join(value.ljust(width) for value, width in zip(row, widths)).rstrip())


def main() -> int:
    exit_code = 0
    try:
        captures, show_table = choose_captures()
        results = []
        for path in captures:
            try:
                count = count_probe_sources(path)
            except (OSError, RuntimeError) as error:
                print(f"Analyze {path.name}: {error}", file=sys.stderr)
                exit_code = 1
                if show_table:
                    results.append((path.name, "error"))
            else:
                if show_table:
                    results.append((path.name, str(count)))
                else:
                    print(f"{path.name}: {count} unique probe-request source addresses")
        if show_table:
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
