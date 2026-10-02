"""Verify installation health. Reports verified vs unverified honestly.

Cannot prove a CI check blocks without branch-protection API access, so
required-check status is always unverified locally. Stdlib only.
"""

import argparse
import os
import sys

VERSION = "0.1.0"


def check_repo(root):
    """Return list of (name, ok, detail) checks."""
    results = []
    config = os.path.join(root, "scripts", "lane-config.yaml")
    results.append(("config", os.path.isfile(config),
                    "lane config present" if os.path.isfile(config)
                    else "lane config missing"))
    hook = os.path.join(root, "hooks", "pre-push.sh")
    results.append(("hook-template", os.path.isfile(hook),
                    "hook template present" if os.path.isfile(hook)
                    else "hook template missing"))
    workflow = os.path.join(root, ".github", "workflows", "sdlc-gate.yml")
    results.append(("ci-template", os.path.isfile(workflow),
                    "CI template present" if os.path.isfile(workflow)
                    else "CI template missing"))
    results.append(("required-check", False,
                    "unverified: mark the CI check required in branch "
                    "protection before it blocks merges"))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check install health")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    print("doctor %s" % VERSION)
    failed = 0
    for name, ok, detail in check_repo(args.root):
        status = "verified" if ok else "unverified"
        if name == "required-check":
            status = "unverified"
        print("%s: %s - %s" % (name, status, detail))
        if not ok and name != "required-check":
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
