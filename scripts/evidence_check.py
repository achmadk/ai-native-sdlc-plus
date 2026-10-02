"""Verify required evidence exists for a lane. Local warns fail-open, CI fails closed.

Checks presence only, never quality. Stdlib only, no network.
"""

import argparse
import os
import sys

REQUIRED = {
    "Lite": ["intent_block", "test_changes", "trace_block"],
    "Standard": ["spec_link", "test_changes", "trace_block", "review_notes"],
    "Critical": ["intent_link", "spec_link", "threat_note", "test_changes",
                 "trace_block", "review_notes", "rollout_plan"],
}


def check(lane, present):
    """Return list of missing evidence names."""
    required = REQUIRED.get(lane, REQUIRED["Standard"])
    return [name for name in required if name not in present]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check lane evidence")
    parser.add_argument("--lane", default="Standard")
    parser.add_argument("--present", nargs="*", default=[],
                        help="evidence names present, e.g. spec_link test_changes")
    parser.add_argument("--ci", action="store_true",
                        help="fail closed in CI; otherwise warn fail-open")
    args = parser.parse_args(argv)
    lane = args.lane if args.lane in REQUIRED else "Standard"
    missing = check(lane, set(args.present))
    if not missing:
        print("evidence ok for %s" % lane)
        return 0
    message = "missing evidence for %s: %s" % (lane, ", ".join(missing))
    if args.ci:
        print("FAIL: %s" % message)
        return 1
    print("WARNING: %s (local, not blocking)" % message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
