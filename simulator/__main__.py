#!/usr/bin/env python3
"""
LogShield Simulator — Laptop 1
===============================
Interactive CLI for emitting synthetic attack scenarios to Laptop 2.

Usage
-----
    python -m simulator            # Interactive menu (Laptop 1 hackathon demo)
    python -m simulator -s A       # Single scenario
    python -m simulator -s F       # Demo kill-chain (CRITICAL incident)
    python -m simulator -s ALL     # All scenarios A → F
    python -m simulator -s B -d 0.1  # Fast replay (0.1s delay)
    python -m simulator -s F --loop  # Continuous stream (Ctrl-C to stop)

Environment
-----------
    LOGSHIELD_SERVER_HOST  default: 127.0.0.1
    LOGSHIELD_SERVER_PORT  default: 8000
"""

import argparse
import os
import sys
import time

# Allow running as  python -m simulator  from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from simulator.client import BASE_URL, post_batch
from simulator.event_generator import SCENARIOS


BANNER = r"""
  ╔══════════════════════════════════════════════════════════╗
  ║        LogShield  Synthetic Attack Simulator             ║
  ║        Laptop 1  →  Laptop 2 AI Engine                   ║
  ╚══════════════════════════════════════════════════════════╝
"""


def print_menu() -> None:
    print(BANNER)
    print(f"  Engine target: {BASE_URL}\n")
    for key, (desc, _) in SCENARIOS.items():
        print(f"  [{key}]  {desc}")
    print("  [ALL] Run A → F sequentially")
    print("  [Q]   Quit\n")


def run_scenario(key: str, delay: float, verbose: bool = True) -> None:
    key = key.upper()
    if key not in SCENARIOS:
        print(f"Unknown scenario '{key}'. Choose A-F or ALL.", file=sys.stderr)
        return

    desc, factory = SCENARIOS[key]
    events = factory()
    print(f"\n  ▶ Scenario {key}: {desc}")
    print(f"    {len(events)} events → {BASE_URL}  (delay={delay}s)\n")
    post_batch(events, delay=delay, verbose=verbose)
    print(f"\n  ✔ Scenario {key} complete.\n")


def interactive_loop(delay: float) -> None:
    while True:
        print_menu()
        choice = input("  Select scenario (A-F / ALL / Q): ").strip().upper()
        if choice in ('Q', 'QUIT', 'EXIT', ''):
            print("  Goodbye.\n")
            break
        elif choice == 'ALL':
            for key in SCENARIOS:
                run_scenario(key, delay=delay)
                time.sleep(1)
        elif choice in SCENARIOS:
            run_scenario(choice, delay=delay)
        else:
            print(f"  Invalid choice '{choice}'. Try again.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m simulator",
        description="LogShield synthetic log emitter (Laptop 1)",
    )
    parser.add_argument(
        "-s", "--scenario",
        metavar="SCENARIO",
        default=None,
        help="Scenario letter A-F, or ALL. Omit for interactive menu.",
    )
    parser.add_argument(
        "-d", "--delay",
        type=float,
        default=0.4,
        metavar="SECONDS",
        help="Inter-event delay in seconds (default: 0.4)",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Repeat the chosen scenario indefinitely until Ctrl-C",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress per-event output",
    )
    args = parser.parse_args()

    if args.scenario is None:
        # Interactive menu
        interactive_loop(delay=args.delay)
        return

    s = args.scenario.upper()
    if s == 'ALL':
        keys = list(SCENARIOS.keys())
    elif s in SCENARIOS:
        keys = [s]
    else:
        print(f"Unknown scenario '{s}'. Valid: A-F or ALL", file=sys.stderr)
        sys.exit(1)

    if args.loop:
        print(f"  Looping scenario(s) {keys} — Ctrl-C to stop\n")
        try:
            while True:
                for key in keys:
                    run_scenario(key, delay=args.delay, verbose=not args.quiet)
                time.sleep(2)
        except KeyboardInterrupt:
            print("\n  Stopped.")
    else:
        for key in keys:
            run_scenario(key, delay=args.delay, verbose=not args.quiet)


if __name__ == '__main__':
    main()
