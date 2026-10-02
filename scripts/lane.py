"""Classify changed paths into Lite / Standard / Critical from a config file.

First match wins: Critical, then Standard, then Lite. Ambiguous or
malformed input escalates to Standard, never Lite. Stdlib only.
"""

import argparse
import fnmatch
import sys


def load_rules(config_path):
    """Parse the small lane-config.yaml subset we rely on."""
    sections = {"critical": [], "standard": [], "lite": []}
    current = None
    try:
        with open(config_path, encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("version:"):
                    continue
                if line.endswith(":") and line[:-1] in sections:
                    current = line[:-1]
                    continue
                if line.startswith("- ") and current:
                    pattern = line[2:].strip().strip('"').strip("'")
                    if pattern:
                        sections[current].append(pattern)
    except OSError as exc:
        return None, "cannot read config: %s" % exc
    if not any(sections.values()):
        return None, "config has no rules"
    return sections, ""


def classify(paths, rules):
    """Return (lane, reason). Malformed or empty input escalates."""
    if not paths:
        return "Standard", "no paths supplied, escalated"
    clean = []
    for item in paths:
        if not isinstance(item, str) or not item.strip():
            return "Standard", "malformed path entry, escalated"
        text = item.strip()
        if text.startswith("/") or ".." in text.split("/"):
            return "Standard", "absolute or traversal path escalated: %s" % text
        clean.append(text)
    for lane in ("Critical", "Standard", "Lite"):
        for pattern in rules[lane.lower()]:
            for path in clean:
                if fnmatch.fnmatch(path, pattern):
                    return lane, "matched %s rule %s" % (lane, pattern)
    return "Standard", "no rule matched, escalated"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Classify change lane")
    parser.add_argument("--paths", nargs="*", default=[])
    parser.add_argument("--config", default="scripts/lane-config.yaml")
    args = parser.parse_args(argv)
    rules, error = load_rules(args.config)
    if rules is None:
        print("Standard: %s" % error)
        return 0
    lane, reason = classify(args.paths, rules)
    print("%s: %s" % (lane, reason))
    return 0


if __name__ == "__main__":
    sys.exit(main())
