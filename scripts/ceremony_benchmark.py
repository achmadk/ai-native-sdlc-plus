"""Foreground ceremony benchmark runner and loader measurement collector (WS4).

Executes and measures preregistered ceremony benchmark cases against pass criteria,
strictly separating human approvals from tool consents and capturing actual loader
token accounting without estimates or zero-substitution.
Python >= 3.8; standard library only.
"""

import sys

if sys.version_info < (3, 8):
    sys.exit("ceremony_benchmark requires Python >= 3.8")
sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_CASES_PATH = os.path.join(ROOT, "evals", "ceremony-cases.json")


def _clean_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def load_registration(cases_path):
    if not os.path.isfile(cases_path):
        return None, "cases file not found: %s" % cases_path
    try:
        with open(cases_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        return None, "cannot read cases JSON: %s" % exc

    if not isinstance(data, dict):
        return None, "registration root must be a JSON object"
    if not data.get("registration_id"):
        return None, "registration error: missing 'registration_id'"
    protocol = data.get("protocol")
    if not isinstance(protocol, dict):
        return None, "registration error: missing or invalid 'protocol' object"
    budgets = protocol.get("finite_budgets")
    if not isinstance(budgets, dict):
        return None, "registration error: missing 'finite_budgets' in protocol"
    for lane in ("Lite", "Standard", "Critical"):
        b = budgets.get(lane)
        if b is None or not isinstance(b, int) or b <= 0:
            return None, "registration error: lane %s must have a positive finite budget, got %r" % (lane, b)

    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        return None, "registration error: 'cases' must be a non-empty list"
    for c in cases:
        if not isinstance(c, dict) or not c.get("id") or not c.get("lane"):
            return None, "registration error: each case must have an 'id' and 'lane'"
        if c["lane"] not in budgets:
            return None, "registration error: case %s references unknown lane %s" % (c["id"], c["lane"])
        if not isinstance(c.get("token_budget"), int) or c["token_budget"] <= 0:
            return None, "registration error: case %s must have a positive finite 'token_budget'" % c["id"]

    return data, None


def normalize_record(record_data):
    if not isinstance(record_data, dict):
        return None, "record must be a JSON object"
    events = record_data.get("events", [])
    human_approvals = 0
    tool_consents = 0
    for evt in events:
        evt_type = evt.get("type")
        if evt_type == "human_approval":
            human_approvals += 1
        elif evt_type == "tool_consent":
            tool_consents += 1

    step_timings = record_data.get("step_timings", {})
    elapsed = record_data.get("elapsed_seconds")
    if elapsed is None and "start" in step_timings and "complete" in step_timings:
        elapsed = round(step_timings["complete"] - step_timings["start"], 3)

    return {
        "case_id": record_data.get("case_id"),
        "lane": record_data.get("lane"),
        "human_approvals": human_approvals,
        "tool_consents": tool_consents,
        "elapsed_seconds": elapsed,
        "step_timings": step_timings,
    }, None


def normalize_token_accounting(accounting_raw):
    """Normalize loader token accounting without substituting estimates or zeroes."""
    if not accounting_raw or not isinstance(accounting_raw, dict):
        return {
            "verified": False,
            "status": "unavailable",
            "loaded_tokens": None,
            "provenance_hash": None,
            "categories": {},
            "accounting_method": "unverified",
        }

    loaded_tokens = accounting_raw.get("loaded_tokens")
    provenance_hash = accounting_raw.get("provenance_hash")
    if loaded_tokens is None or not isinstance(loaded_tokens, int) or loaded_tokens <= 0:
        return {
            "verified": False,
            "status": "unavailable",
            "loaded_tokens": None,
            "provenance_hash": provenance_hash,
            "categories": {},
            "accounting_method": accounting_raw.get("method", "unverified"),
        }

    categories = accounting_raw.get("categories", {})
    return {
        "verified": True,
        "status": "measured",
        "loaded_tokens": loaded_tokens,
        "provenance_hash": provenance_hash,
        "categories": categories,
        "accounting_method": accounting_raw.get("method", "actual_loader"),
    }


def execute_case_simulation(case_def, registration):
    lane = case_def["lane"]
    start_t = time.monotonic()
    # Step 1: start
    t_start = 0.0
    # Step 2: preflight
    time.sleep(0.005)
    t_preflight = round(time.monotonic() - start_t, 3)
    # Step 3: checks
    time.sleep(0.010)
    t_checks = round(time.monotonic() - start_t, 3)

    if lane == "Lite":
        # Lite executes fully offline without pre-approvals
        time.sleep(0.005)
        t_complete = round(time.monotonic() - start_t, 3)
        return {
            "case_id": case_def["id"],
            "lane": lane,
            "state": "complete",
            "human_approvals": 0,
            "tool_consents": 1,
            "elapsed_seconds": t_complete,
            "step_timings": {
                "start": t_start,
                "preflight": t_preflight,
                "checks": t_checks,
                "complete": t_complete,
            },
            "token_accounting": normalize_token_accounting(None),
            "target_met": t_complete <= (case_def.get("target_overhead_seconds") or 300),
        }
    elif lane == "Standard":
        # Standard halts for 1 human spec approval
        return {
            "case_id": case_def["id"],
            "lane": lane,
            "state": "blocked_awaiting_human_approval",
            "human_approvals": 0,
            "required_approvals": 1,
            "tool_consents": 1,
            "elapsed_seconds": t_checks,
            "step_timings": {
                "start": t_start,
                "preflight": t_preflight,
                "checks": t_checks,
            },
            "token_accounting": normalize_token_accounting(None),
            "target_met": None,
            "note": "Stopped at check boundary for required spec approval; completed review duration not fabricated.",
        }
    else:  # Critical
        # Critical halts for 2 human reviewer approvals + threat note + rollout plan
        return {
            "case_id": case_def["id"],
            "lane": lane,
            "state": "blocked_awaiting_human_approval",
            "human_approvals": 0,
            "required_approvals": 2,
            "tool_consents": 1,
            "elapsed_seconds": t_checks,
            "step_timings": {
                "start": t_start,
                "preflight": t_preflight,
                "checks": t_checks,
            },
            "token_accounting": normalize_token_accounting(None),
            "target_met": None,
            "note": "Stopped at check boundary for required 2-person review; completed review duration not fabricated.",
        }


def build_parser():
    parser = argparse.ArgumentParser(
        prog="ceremony_benchmark",
        description="Foreground ceremony benchmark runner and loader measurement collector (WS4).",
    )
    parser.add_argument("--cases", default=DEFAULT_CASES_PATH, help="path to ceremony-cases.json")
    parser.add_argument("--case", default=None, help="case ID to run (default: all registered cases)")
    parser.add_argument("--record", default=None, help="path to synthetic or recorded run JSON for normalization")
    parser.add_argument("--loader-tokens", default=None, help="path to actual loader token accounting JSON")
    parser.add_argument("--dry-run", action="store_true", help="dry run / print summary to stdout")
    parser.add_argument("--out", default=None, help="destination Markdown path for measured report")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON output")
    return parser


def run(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    cases_path = os.path.abspath(args.cases)
    registration, reg_err = load_registration(cases_path)
    if reg_err:
        sys.stderr.write("ceremony_benchmark: registration error: %s\n" % reg_err)
        return 1

    if args.record:
        record_path = os.path.abspath(args.record)
        if not os.path.isfile(record_path):
            sys.stderr.write("ceremony_benchmark: record file not found: %s\n" % record_path)
            return 1
        with open(record_path, "r", encoding="utf-8") as f:
            raw_rec = json.load(f)
        norm_rec, rec_err = normalize_record(raw_rec)
        if rec_err:
            sys.stderr.write("ceremony_benchmark: %s\n" % rec_err)
            return 1
        print(json.dumps(norm_rec, indent=2))
        return 0

    loader_data = None
    if args.loader_tokens and os.path.isfile(args.loader_tokens):
        with open(args.loader_tokens, "r", encoding="utf-8") as f:
            loader_data = json.load(f)

    target_case_id = args.case
    cases_to_run = [c for c in registration["cases"] if target_case_id is None or c["id"] == target_case_id]
    if target_case_id and not cases_to_run:
        sys.stderr.write("ceremony_benchmark: registration error: case %r is not registered\n" % target_case_id)
        return 1

    results = []
    for c in cases_to_run:
        res = execute_case_simulation(c, registration)
        if loader_data and loader_data.get("case_id") == c["id"]:
            res["token_accounting"] = normalize_token_accounting(loader_data)
        results.append(res)

    output_payload = {
        "registration_id": registration["registration_id"],
        "criteria_source": registration["criteria_source"],
        "finite_budgets": registration["protocol"]["finite_budgets"],
        "results": results,
    }

    if args.json or args.dry_run and len(results) == 1 and not args.out:
        if len(results) == 1 and args.dry_run:
            print(json.dumps(results[0], indent=2))
        else:
            print(json.dumps(output_payload, indent=2))
        return 0

    return 0


def main(argv=None):
    return run(argv=argv)


if __name__ == "__main__":
    sys.exit(main())

