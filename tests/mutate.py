"""Tiny mutation check: break the gate in specific ways, confirm the tests notice.

Usage: python3 tests/mutate.py        (exit 1 if any non-equivalent mutant survives)
Each mutant is (file, old, new, equivalent?). 'Equivalent' means the change cannot alter
observable behaviour (defence in depth), so surviving it is expected and documented.
"""
import concurrent.futures
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L, E, D = "scripts/lane.py", "scripts/evidence_check.py", "scripts/doctor.py"
H, HD, C = "hooks/pre-push.sh", "hooks/pre-push", "skills/context-pack/scripts/check_brief.py"
S, R, G = "skills/spec-first/scripts/check_spec.py", "skills/verify-and-evals/scripts/redgreen.py", "skills/ai-sdlc/assets/ci-generic.sh"
# Which test modules can possibly observe a change to each file (lane.py is imported by the others).
TESTS = {L: ["tests.test_lane", "tests.test_evidence_check", "tests.test_hook", "tests.test_templates", "tests.test_doctor"],
         E: ["tests.test_evidence_check", "tests.test_templates", "tests.test_hook"], D: ["tests.test_doctor"],
         H: ["tests.test_hook"], HD: ["tests.test_hook"], C: ["tests.test_check_brief", "tests.test_templates"],
         S: ["tests.test_check_spec", "tests.test_templates"], R: ["tests.test_redgreen", "tests.test_templates"],
         G: ["tests.test_ci_generic"]}

MUTANTS = [
    (L, "top = max(per_path", "top = min(per_path", False),
    (L, 'return "Standard", None', 'return "Lite", None', False),
    (L, 'compile_pattern(pattern, name == "critical")', "compile_pattern(pattern, False)", False),
    (L, '(pattern + " (built-in)", compile_pattern(pattern, True))', '(pattern + " (built-in)", compile_pattern(pattern, False))', False),
    (L, '    "scripts/lane-config.yaml",\n', "", False),
    (L, '    ".github/workflows/**",\n', "", False),
    (L, '    "hooks/**",\n', "", False),
    (L, 'text.startswith("/") or re.match', 'False or re.match', False),
    (L, 'if ".." in text.split("/"):', "if False:", False),
    (L, "if _CONTROL_CHARS.search(item):", "if False:", False),
    (L, '"--no-renames", ', "", False),
    (L, '"-z",\n', "\n", False),
    (L, "if not _REF_OK.match(ref or \"\"):", "if False:", False),
    (L, "if version != str(CONFIG_VERSION):", "if False:", False),
    (L, 'raise ConfigError("line %d: unknown key %r (allowed: %s)" % (number, key, allowed))', "pass", False),
    (L, "return 3 if args.strict else 0", "return 0", False),
    (L, 'unicodedata.normalize("NFC", text)', "text", False),
    (L, 'out.append("[^/]*")', 'out.append(".*")', False),
    (L, 'out.append("(?:.*/)?")', 'out.append("(?:.*/)")', False),
    (L, "if text.count(\"**\") > MAX_DOUBLE_STAR:", "if False:", False),
    (L, 'if not any(sections[name] for name in LANE_SECTIONS):', "if False:", False),
    (E, "MIN_SECTION_CHARS = 20", "MIN_SECTION_CHARS = 19", False),
    (E, "MIN_SECTION_CHARS = 20", "MIN_SECTION_CHARS = 21", False),
    (E, "lanelib.max_lane(computed, declared, floor)", "lanelib.max_lane(computed, floor)", False),
    (E, "lanelib.max_lane(computed, declared, floor)", "lanelib.max_lane(computed, declared)", False),
    (E, "if args.ci and args.present is not None:", "if False:", False),
    (E, "inside = os.path.commonpath([root, full]) == root", "inside = True", False),
    (E, "if os.path.getsize(full) == 0:", "if False:", False),
    (E, '.replace("::", ": :")', "", False),
    (E, "if len(text) > MAX_BODY_BYTES:", "if False:", False),
    (E, 'lane in ("Lite", "Standard") and all(', 'lane in ("Lite", "Standard", "Critical") and all(', False),
    (E, "if meaningful_chars(match.group(1)) >= MIN_WAIVER_CHARS:", "if True:", False),
    (E, "if next_level <= level:", "if next_level < level:", False),
    (E, "        return 1\n    say(", "        return 0\n    say(", False),
    (E, "if in_fence:\n            continue\n        match = pattern.match(line)", "if False:\n            continue\n        match = pattern.match(line)", False),
    (E, 'if not in_fence:\n            match = re.match', 'if True:\n            match = re.match', False),
    (E, 'if not path or path.startswith("/") or ".." in path.replace("\\\\", "/").split("/"):', 'if not path:', True),
    # --- doctor.py ---
    (D, r'if re.search(r"\bpull_request_target\b", text):', "if False:", False),
    (D, r'depth = re.search(r"fetch-depth\s*:\s*0\b", text)', "depth = True", False),
    (D, "trusted = bool(trusted_dir) and re.search(", "trusted = True or re.search(", False),
    (D, "if not _SHA.match(ref) and label not in unpinned:", "if label not in unpinned:", False),
    (D, "covered = has_owner", "covered = True", False),
    (D, "    if missing:\n", "    if False:\n", False),
    (D, 'ln.strip() and "__pycache__" not in ln and not ln.endswith(".pyc")', "ln.strip()", False),
    (D, 'if lane_ != "Critical":', "if False:", False),
    (D, 'if counts["critical"] == 0:', "if False:", False),
    (D, "failed = counts[FAIL] > 0 or (args.strict and counts[WARN] > 0)", "failed = counts[FAIL] > 0", False),
    (D, "failed = counts[FAIL] > 0 or (args.strict and counts[WARN] > 0)", "failed = False", False),
    (D, "results.append((name, missing_status, \"%s missing\" % rel))", "results.append((name, UNVERIFIED, \"%s missing\" % rel))", False),
    (D, "elif not errors:", "elif False:", False),
    (D, 'if item.get("integration_id") in (None, 0, -1):', "if False:", False),
    (D, 'if item.get("app_id") in (None, 0, -1):', "if False:", False),
    (D, "if admins_enforced is False:", "if admins_enforced is not None:", False),
    (D, "if total >= MIN_FILES_FOR_SHARE and", "if True and", False),
    (D, "sys.dont_write_bytecode = True", "sys.dont_write_bytecode = False", False),
    (D, 'if code == 0 and out.strip() == "true":', 'if code == 0 and out.strip() == "false":', False),
    (D, 'return code == 0 and out.strip() == "true"', "return True", False),
    (D, "return 1 if failed else 0", "return 0", False),
    (D, "if os.path.realpath(scripts_dir) == os.path.realpath(HERE):", "if False:", False),
    (D, "    if drifted:\n", "    if False:\n", False),
    # --- evidence_check.py --diff-only ---
    (E, "if args.diff_only and args.ci:", "if False and args.ci:", False),
    (E, "if args.diff_only and not auto:", "if False and not auto:", False),
    (E, "    if args.diff_only:\n        lane = lanelib.max_lane(computed, floor)", "    if False:\n        lane = lanelib.max_lane(computed, floor)", False),
    (E, 'owed = [name for name in REQUIRED[lane] if name != "test_changes"]', "owed = []", False),
    (E, "        if not found[0]:\n            detail = ", "        if False:\n            detail = ", False),
    (E, '("diff checks ok for %s (PR description items are checked in CI)" if args.diff_only', '("diff checks ok for %s (PR description items are checked in CI)" if False', False),
    # --- doctor.py hook logic ---
    (D, "    if not os.path.isfile(target):\n", "    if False:\n", False),
    (D, "if HOOK_MARKER not in text:", "if False:", False),
    (D, "if not os.access(target, os.X_OK):", "if False:", False),
    # --- hooks/pre-push.sh ---
    (H, "trap 'exit 0' EXIT", "", True),
    (H, '[ "${SDLC_HOOK:-}" = "off" ] && exit 0', '[ "${SDLC_HOOK:-}" = "never" ] && exit 0', False),
    (H, '[ "$(git config --get sdlc.hook 2>/dev/null)" = "off" ] && exit 0', '[ "$(git config --get sdlc.hook 2>/dev/null)" = "never" ] && exit 0', False),
    (H, "if [ -t 0 ]; then", "if false; then", False),
    (H, "case \"$local_ref\" in refs/heads/*) ;; *) continue ;; esac", "case \"$local_ref\" in refs/heads/*) ;; *) ;; esac", False),
    (H, 'zeros "$local_sha" && continue', 'false && continue', False),
    (H, '[ "$branch" = "$default_branch" ]', '[ "$branch" != "$default_branch" ]', False),
    (H, '</dev/null 2>&1)', '2>&1)', False),
    (H, 'git merge-base "$default_ref" "$local_sha"', 'git merge-base "$default_ref" "$remote_sha"', False),
    (H, "--diff-only --base=", "--base=", False),
    (H, "sed 's/^/sdlc: /'", "cat", False),
    (H, 'if [ -z "$base" ]; then', "if false; then", False),
    (H, "if ! command -v python3 >/dev/null 2>&1; then", "if false; then", False),
    (H, 'if [ ! -f "$tool" ] || [ ! -f "$cfg" ]; then', "if false; then", False),
    (H, "*[!0]*) return 1 ;; *) return 0 ;;", "*[!0]*) return 0 ;; *) return 1 ;;", False),
    (HD, "\nexit 0\n", "\n", False),
    (HD, '"$(dirname "$0")/pre-push.sh"', '"./pre-push.sh"', False),
    # --- check_brief.py ---
    (C, "< today:\n                reason", "<= today:\n                reason", False),
    (C, "if len(summary) > MAX_SUMMARY:", "if len(summary) >= MAX_SUMMARY:", False),
    (C, "if size > MAX_QUOTE:", "if size >= MAX_QUOTE:", False),
    (C, "if total > MAX_ITEMS[lane]:", "if total >= MAX_ITEMS[lane]:", False),
    (C, "if total == 0:", "if False:", False),
    (C, "if _HIDDEN.search(scan):", "if False:", False),
    (C, 'scan = line[1:] if number == 1 and line.startswith("\\ufeff") else line', "scan = line", False),
    (C, "            if pattern.search(line):\n                add(\"ERROR\", number, \"possible secret", "            if False:\n                add(\"ERROR\", number, \"possible secret", False),
    (C, "if number in in_comment else", "if False else", False),
    (C, 'if not restricted and (not summary or summary == "-"):', "if False:", False),
    (C, "            if not governs:\n", "            if False:\n", False),
    (C, "                elif changed:\n", "                elif False:\n", False),
    (C, "                if changed is None:\n", "                if False:\n", False),
    (C, "if reason and not (replaced or marked_stale):", "if reason and False:", False),
    (C, 'elif low.startswith("superseded-by:") and tag.split(":", 1)[1].strip():', 'elif low.startswith("superseded-by:"):', False),
    (C, 'if info["text"] == 0:', "if False:", False),
    (C, "elif info[\"count\"] == 0 and not any(word in gaps_block for word in GAP_WORDS[name]):", "elif False:", False),
    (C, "    if _SCHEME.match(target):", "    if False:", False),
    (C, "    if not inside:", "    if False:", False),
    (C, 'if quote and current != "criteria":', "if False:", False),
    (C, 'elif current == "criteria" and _LISTLINE.match(line):', "elif False:", False),
    (C, 'and lane == "Critical":', ":", False),
    (C, '"--since=%sT23:59:59" % date.isoformat(), "--"] + governs', '"--since=%s" % date.isoformat(), "--"] + governs', False),
    (C, '"--"] + governs', "] + governs", False),
    (C, "elif len(governs) > MAX_GOVERNS:", "elif False:", False),
    (C, "failed = errors > 0 or (args.strict and warnings > 0)", "failed = errors > 0", False),
    (C, "if os.path.getsize(args.brief) > MAX_BYTES:", "if False:", False),
    (C, "    if today is None:", "    if False:", False),
    # --- evidence_check.py: sub-heading titles are structure, not content ---
    (E, "and not (pos in head_positions)", "and not (False)", False),
    # --- check_spec.py ---
    (S, "if len(pass_text) < MIN_PASS_CHARS:", "if len(pass_text) <= MIN_PASS_CHARS:", False),
    (S, r'elif not re.search(r"\d", pass_text):', "elif True:", False),
    (S, "            if cid in criteria:\n", "            if False:\n", False),
    (S, "        if cid not in covered:\n", "        if False:\n", False),
    (S, "            if cid not in criteria:\n", "            if False:\n", False),
    (S, 'if len(why) < MIN_PASS_CHARS or why.lower() in ("n/a", "none"):', "if False:", False),
    (S, 'if ref.lower().startswith("manual:"):', "if False:", False),
    (S, "elif require_tests_exist:", "elif False:", False),
    (S, "if len(criteria) > MAX_CRITERIA[lane]:", "if len(criteria) >= MAX_CRITERIA[lane]:", False),
    (S, '        elif info["text"] == 0:\n', "        elif False:\n", False),
    (S, "        if info is None:\n            add(\"ERROR\", 1, \"%s %s requires", "        if False:\n            add(\"ERROR\", 1, \"%s %s requires", False),
    (S, 'if lane == "Lite" and kind == "spec":\n        return', "if False:\n        return", False),
    (S, "    elif require_approved:", "    elif False:", False),
    (S, 'parse_date(match.group("date")) is None or ', "", False),
    (S, "if author and author[1].strip().lower() == match.group(\"name\").strip().lower():", "if False:", False),
    (S, "RANK[declared[1].title()] < RANK[lane]", "RANK[declared[1].title()] > RANK[lane]", False),
    (S, '_BLANK = re.compile(r"___|\\bTBD\\b")', '_BLANK = re.compile(r"___")', False),
    (S, "if _HIDDEN.search(scan):", "if False:", False),
    (S, "            if pattern.search(line):\n                add(\"ERROR\", number, \"possible secret", "            if False:\n                add(\"ERROR\", number, \"possible secret", False),
    (S, 'if current == "criteria" and _LIST.match(line):', "if False:", False),
    (S, 'elif current == "tests" and _LIST.match(line):', "elif False:", False),
    (S, 'if "criteria" in sections and not criteria and kind == "spec":', "if False:", False),
    (S, 'scan = line[1:] if number == 1 and line.startswith("\\ufeff") else line', "scan = line", False),
    (S, "    if not inside:\n", "    if False:\n", False),
    (S, "    if not os.path.isfile(full):\n", "    if False:\n", False),
    (S, "    if not _PATHLIKE.search(target):\n", "    if False:\n", False),
    (S, "failed = errors > 0 or (args.strict and warnings > 0)", "failed = errors > 0", False),
    (S, "return 1 if failed else 0", "return 0", False),
    (S, "if os.path.getsize(args.spec) > MAX_BYTES:", "if False:", False),
    (S, "            elif current in sections:\n                add(\"WARN\", number, \"section", "            elif False:\n                add(\"WARN\", number, \"section", False),
    (S, "            if current is None:\n                add(\"WARN\", number, \"unknown section", "            if False:\n                add(\"WARN\", number, \"unknown section", False),
    # --- redgreen.py ---
    (R, "    if not tests:\n        result[\"verdict\"] = \"NO_TESTS\"", "    if False:\n        result[\"verdict\"] = \"NO_TESTS\"", False),
    (R, 'if red == "GREEN":', "if False:", False),
    (R, 'elif "FLAKY" in (red, green):', "elif False:", False),
    (R, 'elif green == "RED":', "elif False:", False),
    (R, 'if "ERROR" in (red, green):', "if False:", False),
    (R, '    if all(failed):\n        return "RED"', '    if any(failed):\n        return "RED"', False),
    (R, 'if any(run["error"] for run in runs):', "if False:", False),
    (R, "if any(pattern.search(line) for _, pattern in SECRETS):", "if False:", False),
    (R, '_CONTROL.sub("", line)', "line", False),
    (R, "kept[-TAIL_LINES:]", "kept", False),
    (R, "line if len(line) <= MAX_LINE else", "line if True else", False),
    (R, '"--diff-filter=AMT"', '"--diff-filter=AMTD"', False),
    (R, '"--literal-pathspecs", ', "", False),
    (R, "env=clean_env()", "env=None", False),
    (R, "if not 1 <= args.repeat <= MAX_REPEAT or args.timeout < 1:", "if False:", False),
    (R, "    if not command:\n", "    if False:\n", False),
    (R, 'return 0 if result["verdict"] == "PASS" else 1', "return 0", False),
    (R, "        if setup:\n", "        if False:\n", False),
    (R, "shutil.rmtree(scratch, ignore_errors=True)", "pass", False),
    # Equivalent: resolve() appends "^{commit}" to the ref, and every later git call receives only full SHAs, so an unsafe ref is
    # rejected by git itself even without this check. The check is kept as defence in depth.
    (R, "if not _REF_OK.match(ref or \"\"):", "if False:", True),
    # --- ci-generic.sh ---
    (G, '[ "${#sha}" -ge 40 ] ||', '[ "${#sha}" -ge 1 ] ||', False),
    (G, '  case "$sha" in *[!0-9a-f]*) die 2 "not a commit SHA: $sha" ;; esac\n', "", False),
    (G, '[ -f "$SDLC_PR_BODY_FILE" ] ||', "true ||", False),
    (G, 'git rev-parse -q --verify "$SDLC_BASE^{commit}" >/dev/null 2>&1 ||', "true ||", False),
    (G, 'git archive "$SDLC_BASE" scripts', 'git archive "$SDLC_HEAD" scripts', False),
    (G, '--config "$tmp/scripts/lane-config.yaml"', "--config scripts/lane-config.yaml", False),
    (G, "trap 'rm -rf \"$tmp\"' EXIT", "", False),
    (G, 'command -v python3 >/dev/null 2>&1 || die 2', "true || die 2", False),
    (G, '[ -f "$tmp/scripts/evidence_check.py" ] && [ -f "$tmp/scripts/lane.py" ] && [ -f "$tmp/scripts/lane-config.yaml" ] ||', "true ||", False),
    (G, ': "${SDLC_BASE:=}" "${SDLC_HEAD:=}" "${SDLC_PR_BODY_FILE:=}"\n', "", False),
    (G, '--pr-body-file "$SDLC_PR_BODY_FILE"', "", False),
    (G, "python3 \"$tmp/scripts/evidence_check.py\" --ci \\", "python3 \"$tmp/scripts/evidence_check.py\" \\", False),
]


def run_tests(tree, modules=None):
    cmd = [sys.executable, "-m", "unittest"] + (modules or ["discover", "-s", "tests"])
    proc = subprocess.run(cmd, cwd=tree, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode == 0


def try_mutant(number, mutant):
    rel, old, new, is_equiv = mutant
    tree = tempfile.mkdtemp()
    try:
        shutil.copytree(ROOT, tree, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", ".git"))
        path = os.path.join(tree, rel)
        with open(path) as handle:
            source = handle.read()
        if old not in source:
            return number, mutant, "stale"
        with open(path, "w") as handle:
            handle.write(source.replace(old, new))
        for module in TESTS[rel]:           # stop at the first module that notices: most kills are fast
            if not run_tests(tree, [module]):
                return number, mutant, "killed"
        return number, mutant, "survived"
    finally:
        shutil.rmtree(tree, ignore_errors=True)


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    if not run_tests(ROOT):
        print("baseline tests fail on UNMUTATED code; mutation results would be meaningless")
        return 2
    chosen = [(i, m) for i, m in enumerate(MUTANTS, 1) if only in m[0]]
    workers = max(1, min(8, os.cpu_count() or 1))
    killed = survived = equivalent = 0
    bad = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for number, (rel, old, new, is_equiv), outcome in pool.map(lambda item: try_mutant(*item), chosen):
            label = "%s: %s" % (rel, old[:60].replace("\n", " "))
            if outcome == "stale":
                print("#%02d STALE    (pattern not found) %s" % (number, label))
                bad.append(number)
            elif outcome == "killed":
                killed += 1
                print("#%02d killed   %s" % (number, label))
            elif is_equiv:
                equivalent += 1
                print("#%02d survived (equivalent, expected) %s" % (number, label))
            else:
                survived += 1
                bad.append(number)
                print("#%02d SURVIVED %s  ->  %s" % (number, label, new[:40].replace("\n", " ")))
            sys.stdout.flush()
    print("\nkilled %d / %d non-equivalent mutants; %d equivalent survivor(s) documented"
          % (killed, killed + survived, equivalent))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
