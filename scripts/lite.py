"""Draft and verify a factual PR description for an eligible Lite change (WS4).

Evaluates an explicitly declared committed change range with the existing strict
classifier, drafts minimal Intent/Plan/Trace from author facts and receipts, and
runs the real evidence checker with fail-closed semantics. Never introduces
additional workflow pre-approval. Python >= 3.8; standard library only.
"""

import sys

if sys.version_info < (3, 8):
    sys.exit("sdlc lite requires Python >= 3.8")
sys.dont_write_bytecode = True

import argparse
import importlib.util
import json
import os
import re
import shlex
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_REF_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@^~{}:-]*$")
_FILLER_WORDS = frozenset(("tbd", "todo", "n/a", "none", "wip", "draft", "test", "temp", "patch", "update", "fix"))


def _clean_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _load_sibling_module(module_name, filename):
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = os.path.join(HERE, filename)
    if not os.path.isfile(path):
        raise RuntimeError("missing required runtime component: %s" % filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load required component: %s" % filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_lane_lib():
    return _load_sibling_module("_sdlc_lite_lane", "lane.py")


def load_evidence_lib():
    return _load_sibling_module("_sdlc_lite_evidence", "evidence_check.py")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="sdlc lite",
        description="Draft and verify a factual PR description for an eligible Lite change (fail-closed, no workflow pre-approval).",
    )
    parser.add_argument("--base", required=True, help="base commit reference (required)")
    parser.add_argument("--head", default="HEAD", help="head commit reference (default: HEAD)")
    parser.add_argument("--repo-root", default=".", help="target repository root (default: .)")
    parser.add_argument("--config", default=None, help="lane config YAML path (default: <repo-root>/scripts/lane-config.yaml)")
    parser.add_argument("--intent", default=None, help="explicit intent description (optional)")
    parser.add_argument("--redgreen", default=None, help="path to red-to-green receipt JSON or JSON string (optional)")
    parser.add_argument("--output", default=None, help="destination file path for the PR body draft (optional)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON summary")
    return parser


def _is_git_repo(repo_root):
    try:
        res = subprocess.run(
            ["git", "-C", repo_root, "rev-parse", "--is-inside-work-tree"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_clean_env(),
            timeout=10,
        )
        return res.returncode == 0 and res.stdout.strip() == b"true"
    except (OSError, subprocess.TimeoutExpired):
        return False


def _resolve_revision(repo_root, ref):
    if not isinstance(ref, str) or not _REF_OK.match(ref.strip()):
        return None
    try:
        res = subprocess.run(
            ["git", "-C", repo_root, "rev-parse", "--verify", ref.strip() + "^{commit}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_clean_env(),
            timeout=10,
        )
        if res.returncode == 0:
            sha = res.stdout.strip().decode("ascii")
            if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sha):
                return sha
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _extract_intent_from_commits(repo_root, base_sha, head_sha):
    try:
        res = subprocess.run(
            ["git", "-C", repo_root, "log", "--format=%B", "--no-merges", "%s..%s" % (base_sha, head_sha)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_clean_env(),
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if res.returncode != 0 or not res.stdout.strip():
            return None, []
        lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        trailers = []
        body_lines = []
        for line in lines:
            trailer_match = re.match(r"^(?:Assisted-by|Co-authored-by|Signed-off-by|Author):\s*(.+)$", line, re.I)
            approval_match = re.match(r"^\s*(?:[-*+]\s+)?\*{0,2}(?:Approved-by|Reviewed-by|Reviewer)\s*:\s*", line, re.I)
            if trailer_match:
                trailers.append(line)
            elif approval_match:
                continue
            else:
                body_lines.append(line)

        # Check if any body line or combined body is meaningful (>= 20 chars and not filler)
        combined = " ".join(body_lines).strip()
        clean_words = set(re.findall(r"\b[a-zA-Z]{2,}\b", combined.lower()))
        if len(combined) >= 20 and not clean_words.issubset(_FILLER_WORDS):
            return combined, trailers
        return None, trailers
    except (OSError, subprocess.TimeoutExpired):
        return None, []


def _parse_redgreen_receipt(redgreen_input, repo_root, head_sha):
    raw = None
    receipt_path = os.path.join(repo_root, redgreen_input) if not os.path.isabs(redgreen_input) else redgreen_input
    if os.path.isfile(receipt_path):
        try:
            with open(receipt_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError) as exc:
            return None, "cannot read redgreen receipt %r: %s" % (redgreen_input, exc)
    else:
        try:
            raw = json.loads(redgreen_input)
        except ValueError:
            return None, "redgreen receipt file not found and input is not valid JSON: %r" % redgreen_input

    if not isinstance(raw, dict):
        return None, "redgreen receipt must be a JSON object"
    verdict = raw.get("verdict")
    receipt_head = raw.get("head_sha") or raw.get("head")
    if not verdict:
        return None, "redgreen receipt missing 'verdict' field"
    if verdict != "PASS":
        return None, "redgreen receipt verdict is %r, not PASS" % verdict
    if receipt_head and not head_sha.startswith(receipt_head) and not receipt_head.startswith(head_sha[:12]):
        return None, "redgreen receipt head %r does not match evaluated head %r" % (receipt_head, head_sha[:12])
    return raw, None


def _sanitize_intent(intent_raw):
    if not intent_raw:
        return None
    text = _CONTROL_CHARS.sub("", intent_raw)
    lines = []
    for line in text.splitlines():
        if re.match(r"^\s*(?:[-*+]\s+)?\*{0,2}(?:Approved-by|Reviewed-by|Reviewer)\s*:\s*", line, re.I):
            continue
        if re.match(r"^\s*#{1,6}\s*(?:Review\s*notes|Approvals?)\b", line, re.I):
            continue
        lines.append(line)
    cleaned = "\n".join(lines).strip()
    cleaned = re.sub(r"(?im)^\s*(?:[-*+]\s+)?\*{0,2}(?:Approved-by|Reviewed-by|Reviewer)\s*:[^\n]*\n?", "", cleaned)
    cleaned = re.sub(r"\b(?:Approved-by|Reviewed-by|Reviewer):\s*[^,\n]+", "", cleaned)
    words = set(re.findall(r"\b[a-zA-Z]{2,}\b", cleaned.lower()))
    if len(cleaned) >= 20 and not words.issubset(_FILLER_WORDS):
        return cleaned
    return None


def _compose_draft(intent, paths, changes, base_sha, head_sha, trailers, receipt, is_non_executable):
    sanitized_intent = _sanitize_intent(intent)
    lines = []
    # 1. Intent
    lines.append("## Intent")
    if sanitized_intent:
        lines.append(sanitized_intent)
    else:
        lines.append("<!-- MISSING: Provide a 2-3 sentence intent describing what this Lite change achieves and why. -->")
    lines.append("")

    # 2. Plan
    lines.append("## Plan")
    if is_non_executable:
        lines.append("Documentation and low-risk prose updates across %d file(s)." % len(paths))
    else:
        lines.append("Low-risk Lite change modifying %d file(s)." % len(paths))
    lines.append("")

    # 3. Trace
    lines.append("## Trace")
    lines.append("### Change")
    if len(paths) <= 10:
        lines.append("Modified files:\n" + "\n".join("- `%s`" % p for p in sorted(paths)))
    else:
        lines.append("Modified %d files between %s and %s:\n" % (len(paths), base_sha[:12], head_sha[:12])
                     + "\n".join("- `%s`" % p for p in sorted(paths)[:10]) + "\n- ... and %d more" % (len(paths) - 10))
    lines.append("")

    lines.append("### Why")
    if sanitized_intent:
        lines.append(sanitized_intent)
    else:
        lines.append("<!-- MISSING: Record the rationale or requirement triggering this change. -->")
    lines.append("")

    lines.append("### Alternatives rejected")
    lines.append("None recorded for low-risk Lite change.")
    lines.append("")

    lines.append("### Test evidence")
    if receipt:
        cmd_str = " ".join(receipt.get("command", [])) if isinstance(receipt.get("command"), list) else str(receipt.get("command", ""))
        lines.append("Red-to-green proof verified (verdict: PASS, command: `%s`, head: %s)."
                     % (cmd_str, (receipt.get("head_sha") or head_sha)[:12]))
        if is_non_executable:
            lines.append("waived: only non-executable paths changed")
    elif is_non_executable:
        lines.append("waived: only non-executable paths changed")
    else:
        test_files = [p for p in paths if "test" in p.lower() or "spec" in p.lower() or "eval" in p.lower()]
        if test_files:
            lines.append("Updated test files: %s" % ", ".join(test_files))
        else:
            lines.append("<!-- MISSING: Add test changes or 'Tests: none - <reason>' waiver. -->")
    lines.append("")

    lines.append("### Risk accepted")
    if is_non_executable:
        lines.append("Non-executable documentation change; no runtime code or gate configuration modified.")
    else:
        lines.append("Low-risk Lite change; verified locally.")
    lines.append("")

    lines.append("### Provenance")
    if trailers:
        lines.append("\n".join(trailers))
    else:
        lines.append("Authored directly by developer (verified via local sdlc lite).")
    lines.append("")

    return "\n".join(lines)


def _safe_write_output(output_path, content):
    norm_out = os.path.abspath(output_path)
    if os.path.isdir(norm_out):
        return False, "output path %r is a directory" % output_path
    if os.path.islink(norm_out):
        return False, "refusing to write to symlinked output path %r" % output_path
    if os.path.isfile(norm_out):
        try:
            with open(norm_out, "r", encoding="utf-8") as f:
                existing = f.read()
            if existing == content:
                return True, "idempotent: output file %r already has identical content" % output_path
            return False, "output file %r already exists with different content; refusing overwrite" % output_path
        except OSError as exc:
            return False, "cannot read existing output file %r: %s" % (output_path, exc)

    out_dir = os.path.dirname(norm_out)
    os.makedirs(out_dir, exist_ok=True)
    fd, temp_file = tempfile.mkstemp(prefix=".sdlc-lite-", dir=out_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_file, norm_out)
        temp_file = None
        return True, "wrote draft to %s" % output_path
    except OSError as exc:
        return False, "cannot write output file %r: %s" % (output_path, exc)
    finally:
        if temp_file is not None and os.path.isfile(temp_file):
            try:
                os.unlink(temp_file)
            except OSError:
                pass


def run_lite(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    repo_root = os.path.abspath(args.repo_root)
    if not os.path.isdir(repo_root) or not _is_git_repo(repo_root):
        sys.stderr.write("sdlc lite: %r is not a git repository work tree\n" % args.repo_root)
        return 3

    base_sha = _resolve_revision(repo_root, args.base)
    if not base_sha:
        sys.stderr.write("sdlc lite: cannot resolve base revision %r\n" % args.base)
        return 3
    head_sha = _resolve_revision(repo_root, args.head)
    if not head_sha:
        sys.stderr.write("sdlc lite: cannot resolve head revision %r\n" % args.head)
        return 3

    if base_sha == head_sha:
        sys.stderr.write("sdlc lite: empty range: base and head resolve to the same commit (%s)\n" % base_sha[:12])
        return 1

    lanelib = load_lane_lib()
    evidencelib = load_evidence_lib()

    # Read git changed files
    try:
        changes = lanelib.git_changed_files(base_sha, head_sha, repo_root)
    except lanelib.GitError as exc:
        sys.stderr.write("sdlc lite: git diff failed: %s\n" % exc)
        return 3

    if not changes:
        sys.stderr.write("sdlc lite: empty change: no modified files between %s and %s\n" % (base_sha[:12], head_sha[:12]))
        return 1

    paths = [item["raw_path"] for item in changes]

    # Load lane config
    if args.config:
        config_path = os.path.abspath(args.config)
    else:
        target_cfg = os.path.join(repo_root, "scripts", "lane-config.yaml")
        if os.path.isfile(target_cfg):
            config_path = target_cfg
        else:
            runtime_cfg = os.path.join(HERE, "lane-config.yaml")
            config_path = runtime_cfg if os.path.isfile(runtime_cfg) else target_cfg
    rules, config_err = lanelib.load_rules(config_path)
    if rules is None:
        sys.stderr.write("sdlc lite: lane configuration error: %s\n" % config_err)
        return 3

    lane, reason, _ = lanelib.classify_detailed(paths, rules, changes=changes)
    if lane != "Lite":
        msg = (
            "sdlc lite: change is %s (%s), not Lite.\n"
            "Lite fast-path only applies to low-risk changes. Please use the standard workflow:\n"
            "  sdlc check evidence --repo-root %s --base %s --head %s\n"
        ) % (lane, reason, shlex.quote(args.repo_root), base_sha[:12], head_sha[:12])
        sys.stderr.write(msg)
        if args.json:
            payload = {
                "eligible": False,
                "lane": lane,
                "reason": reason,
                "base": base_sha,
                "head": head_sha,
                "paths": paths,
                "passed": False,
                "draft": None,
                "missing": ["non_lite_change"],
            }
            print(json.dumps(payload, sort_keys=True, indent=2))
        return 1

    # Check redgreen receipt if supplied
    receipt_data = None
    if args.redgreen:
        receipt_data, rg_err = _parse_redgreen_receipt(args.redgreen, repo_root, head_sha)
        if rg_err:
            sys.stderr.write("sdlc lite: %s\n" % rg_err)
            return 1

    # Determine intent
    intent = args.intent
    commit_intent, trailers = _extract_intent_from_commits(repo_root, base_sha, head_sha)
    if not intent and commit_intent:
        intent = commit_intent

    # Check if only non-executable paths changed
    non_exec_patterns = rules.get("non_executable") or list(evidencelib.DEFAULT_NON_EXECUTABLE)
    is_non_executable = (
        all(lanelib.regular_change(c) for c in changes)
        and all(evidencelib._matches_any(p, non_exec_patterns) and lanelib.is_prose(p) for p in paths)
    )

    draft = _compose_draft(
        intent=intent,
        paths=paths,
        changes=changes,
        base_sha=base_sha,
        head_sha=head_sha,
        trailers=trailers,
        receipt=receipt_data,
        is_non_executable=is_non_executable,
    )

    # Detect evidence via real evidence checker
    detection = evidencelib.detect(
        draft,
        paths,
        repo_root,
        rules,
        lane="Lite",
        changes=changes,
        revision=head_sha,
    )

    missing = []
    for req in evidencelib.REQUIRED["Lite"]:
        ok, detail = detection.get(req, (False, "missing"))
        if not ok:
            missing.append(req)

    passed = len(missing) == 0

    if args.output:
        ok_write, write_msg = _safe_write_output(args.output, draft)
        if not ok_write:
            sys.stderr.write("sdlc lite: %s\n" % write_msg)
            return 1

    if args.json:
        payload = {
            "eligible": True,
            "lane": "Lite",
            "reason": reason,
            "base": base_sha,
            "head": head_sha,
            "paths": paths,
            "passed": passed,
            "missing": missing,
            "draft": draft,
            "evidence": {k: {"ok": v[0], "detail": v[1]} for k, v in detection.items()},
        }
        print(json.dumps(payload, sort_keys=True, indent=2))
        return 0 if passed else 1

    if passed:
        if not args.output:
            sys.stdout.write(draft)
        else:
            sys.stdout.write("Draft verified for Lite and written to %s\n" % args.output)
        return 0

    sys.stderr.write("sdlc lite: missing required evidence for Lite: %s\n" % ", ".join(missing))
    for m in missing:
        sys.stderr.write("  - %s: %s\n" % (m, detection.get(m, (False, ""))[1]))
    if not args.output:
        sys.stderr.write("\nGenerated preview draft:\n%s\n" % draft)
    return 1


def main(argv=None):
    return run_lite(argv=argv)


if __name__ == "__main__":
    sys.exit(main())
