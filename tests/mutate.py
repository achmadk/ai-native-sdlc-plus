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

if __package__:
    from . import support
else:
    import support

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L, E, D = "scripts/lane.py", "scripts/evidence_check.py", "scripts/doctor.py"
H, HD, C = "hooks/pre-push.sh", "hooks/pre-push", "skills/context-pack/scripts/check_brief.py"
S, R, G = "skills/spec-first/scripts/check_spec.py", "skills/verify-and-evals/scripts/redgreen.py", "skills/ai-sdlc/assets/ci-generic.sh"
SI = "skills/spec-first/scripts/spec_inputs.py"
FD, I, AP, BW = "scripts/sdlc.py", "scripts/install.py", "scripts/agent_profiles.py", "scripts/build_wheel.py"
LT, CB = "scripts/lite.py", "scripts/ceremony_benchmark.py"
# Which test modules can possibly observe a change to each file (lane.py is imported by the others).
TESTS = {L: ["tests.test_lane", "tests.test_evidence_check", "tests.test_hook", "tests.test_templates", "tests.test_doctor", "tests.test_ci_security"],
         E: ["tests.test_evidence_check", "tests.test_spec_interop", "tests.test_templates", "tests.test_hook", "tests.test_ci_security"],
         SI: ["tests.test_spec_interop", "tests.test_interop_adapters"],
         D: ["tests.test_doctor.WorkflowChecks", "tests.test_doctor.Basics", "tests.test_doctor.ConfigChecks",
             "tests.test_doctor.HookChecks", "tests.test_doctor.CodeownersChecks", "tests.test_doctor.RemoteChecks",
             "tests.test_doctor.GitState", "tests.test_doctor"],
         H: ["tests.test_hook"], HD: ["tests.test_hook"], C: ["tests.test_check_brief", "tests.test_templates"],
         S: ["tests.test_check_spec", "tests.test_templates"], R: ["tests.test_redgreen", "tests.test_templates"],
         G: ["tests.test_ci_generic", "tests.test_ci_security"],
         FD: ["tests.test_sdlc_cli.PublicCLIContract", "tests.test_sdlc_cli.DoctorAndExplainContract",
              "tests.test_sdlc_cli.RuntimeIsolationContract", "tests.test_sdlc_cli"],
         I: ["tests.test_lifecycle.StatusAndDryRunPlanningContract", "tests.test_lifecycle.UpdateReconciliationContract",
             "tests.test_lifecycle.UninstallContract", "tests.test_lifecycle.LifecycleRaceAndFailureContract",
             "tests.test_agent_profiles.CanonicalPolicyAndRegistryContract"],
         AP: ["tests.test_agent_profiles.ClaudeCursorCopilotCodexProfilesContract",
              "tests.test_agent_profiles.GeminiOpencodeKiloAndHostilePolicyContract",
              "tests.test_agent_profiles.CanonicalPolicyAndRegistryContract"],
         BW: ["tests.test_wheel.WheelPackagingContract", "tests.test_wheel.InstalledWheelExecutionContract"],
         LT: ["tests.test_lite"],
         CB: ["tests.test_ceremony_benchmark"]}

MUTANTS = [
    (L, '    "openspec/config.yaml",\n', "", False),
    (LT, 'if lane != "Lite":', "if False:", False),
    (LT, "if not base_sha:", "if False:", False),
    (LT, "if base_sha == head_sha:", "if False:", False),
    (LT, "if args.redgreen:", "if False:", False),
    (CB, "if reg_err:", "if False:", False),
    (CB, 'if not data.get("registration_id"):', "if False:", False),
    (L, "top = max(per_path", "top = min(per_path", False),
    (L, 'return "Standard", None', 'return "Lite", None', False),
    (L, 'compile_pattern(pattern, name == "critical")', "compile_pattern(pattern, False)", False),
    (L, '(pattern + " (built-in)", compile_pattern(pattern, True))', '(pattern + " (built-in)", compile_pattern(pattern, False))', False),
    (L, '    "scripts/**",\n', "", False),
    (L, '    ".github/workflows/**",\n', "", False),
    (L, '    "hooks/**",\n', "", False),
    (L, '    ".cursor/skills/**",\n', "", False),
    (L, '    ".github/prompts/**",\n', "", False),
    (L, '    ".opencode",\n', "", False),
    (L, '    ".gemini",\n', "", False),
    (L, '    "AGENTS.override.md",\n', "", False),
    (L, 'text.startswith("/") or re.match', 'False or re.match', False),
    (L, 'if ".." in text.split("/"):', "if False:", False),
    (L, "if _CONTROL_CHARS.search(item):", "if False:", False),
    (L, '"--no-renames",\n', "\n", False),
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
    (E, "if int(fields[3]) == 0:", "if False:", False),
    (E, '.replace("::", ": :")', "", False),
    (E, "if len(text) > MAX_BODY_BYTES:", "if False:", False),
    (E, 'and lane in ("Lite", "Standard")\n', 'and lane in ("Lite", "Standard", "Critical")\n', False),
    (E, "if meaningful_chars(match.group(1)) >= MIN_WAIVER_CHARS:", "if True:", False),
    (E, "if next_level <= level:", "if next_level < level:", False),
    (E, "        return 1\n    say(", "        return 0\n    say(", False),
    (E, "if in_fence:\n            continue\n        match = pattern.match(line)", "if False:\n            continue\n        match = pattern.match(line)", False),
    (E, 'if not in_fence:\n            match = re.match', 'if True:\n            match = re.match', False),
    (E, 'if lanelib.clean_path(path)[0] is None:', 'if False:', False),
    # --- doctor.py ---
    (D, '"pull_request_target" not in events', "True", False),
    (D, 'and head_with["fetch-depth"] == 0, FAIL', 'and True, FAIL', False),
    (D, 'add("trusted-tooling", base_ok and head_ok and gate_ok, WARN,', 'add("trusted-tooling", True, WARN,', False),
    (D, "pinned = len(actions) == 2 and not unpinned and all(isinstance(a, str) for a in actions)", "pinned = True", False),
    (D, "covered = has_owner", "covered = True", False),
    (D, "    if missing:\n", "    if False:\n", False),
    (D, 'ln.strip() and "__pycache__" not in ln and not ln.endswith(".pyc")', "ln.strip()", False),
    (D, 'if lane_ != "Critical":', "if False:", False),
    (D, 'if counts["critical"] == 0:', "if False:", False),
    (D, "failed = counts[FAIL] > 0 or (args.strict and counts[WARN] > 0)", "failed = counts[FAIL] > 0", False),
    (D, "failed = counts[FAIL] > 0 or (args.strict and counts[WARN] > 0)", "failed = False", False),
    (D, "results.append((name, missing_status, \"%s missing\" % rel))", "results.append((name, UNVERIFIED, \"%s missing\" % rel))", False),
    (D, "elif not errors:", "elif False:", False),
    (D, 'if (app_id is None or type(item.get("integration_id")) is not int or\n                                item["integration_id"] != app_id):', "if False:", False),
    (D, 'if app_id is None or type(item.get("app_id")) is not int or item["app_id"] != app_id:', "if False:", False),
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
    (H, 'if [ -z "$python_cmd" ]; then', "if false; then", False),
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
    (G, "python3 -I \"$tmp/scripts/evidence_check.py\" --ci \\", "python3 -I \"$tmp/scripts/evidence_check.py\" \\", False),
    # --- sdlc.py (dispatcher bypasses & hidden doctor failures) ---
    (FD, "return 0 if code is None else int(code)", "return 0", False),
    (FD, "for req in required:", "for req in ():", False),
    (FD, 'if status == "FAIL" or (strict and status == "WARN") or status not in ("FAIL", "WARN", "unverified", "info"):',
     'if status == "FAIL" or (False and status == "WARN") or status not in ("FAIL", "WARN", "unverified", "info"):', False),
    (FD, 'if status == "verified":', 'if status in ("verified", "FAIL"):', False),
    (FD, "failed = counts[doctor_mod.FAIL] > 0 or (parsed.strict and counts[doctor_mod.WARN] > 0)", "failed = False", False),
    # --- install.py (unsafe ownership/deletion & dropped generated records) ---
    (I, "recognized.discard(CANONICAL_POLICY)", "recognized.add(CANONICAL_POLICY)", False),
    (I, "unrecognized = sorted(rel for rel in owned if rel not in recognized)", "unrecognized = []", False),
    (I, "if additive:", "if False:", False),
    (I, 'elif snap["record"] != owned_rec:', "elif False:", False),
    # --- agent_profiles.py (native manual command safety) ---
    (AP, '"disable-model-invocation: true\\n"', '"disable-model-invocation: false\\n"', False),
    # --- build_wheel.py (required source integrity) ---
    (BW, "if license_snap is None:", "if False:", False),
    # --- Interoperability controls (spec_inputs.py & evidence_check.py) ---
    (SI, "if (sf, u_key) not in mapped_units:", "if False:", False),
    (SI, '    if lane == "Critical":\n        for risk_file', '    if False:\n        for risk_file', False),
    (E, "resolve_repo_file(link_target(spec_val), repo_root, revision, lane=lane, return_bundle_info=True)", "resolve_repo_file(link_target(spec_val), repo_root, None, lane=lane, return_bundle_info=True)", False),
    (E, '_spec_inputs_path = os.path.join(_root_dir, "skills", "spec-first", "scripts", "spec_inputs.py")', '_spec_inputs_path = os.path.join(repo_root or _root_dir, "skills", "spec-first", "scripts", "spec_inputs.py")', False),
]


def run_tests(tree, modules=None):
    cmd = [sys.executable, "-B", "-m", "unittest"] + (
        ["--failfast"] + modules if modules else ["discover", "-s", "tests", "-v"])
    proc = subprocess.run(cmd, cwd=tree, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not modules or proc.returncode:
        sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
        sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
    return proc.returncode == 0


def try_mutant(number, mutant):
    rel, old, new, is_equiv = mutant
    tree = tempfile.mkdtemp()
    try:
        shutil.copytree(ROOT, tree, dirs_exist_ok=True, symlinks=True, ignore_dangling_symlinks=True,
                        ignore=shutil.ignore_patterns("__pycache__", ".git", ".codegraph", ".omo", "*.pyc"))
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
        support.remove_tree(tree)


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    chosen = [(i, m) for i, m in enumerate(MUTANTS, 1) if only in m[0]]
    modules_to_check = set()
    for _, (rel, _, _, _) in chosen:
        modules_to_check.update(TESTS.get(rel, []))
    baseline_modules = list(modules_to_check) if (only and modules_to_check) else None
    if not run_tests(ROOT, baseline_modules):
        print("baseline tests fail on UNMUTATED code; mutation results would be meaningless")
        return 2
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
