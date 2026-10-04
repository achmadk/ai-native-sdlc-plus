"""Verify installation health. Honest about what it can and cannot verify.

Statuses (one per check, printed as "name: status - detail"):
  verified    checked here and true
  FAIL        checked here and wrong: the gate will not work, or is unsafe
  WARN        works, but there is a risk or drift to look at (counts as FAIL with --strict)
  unverified  cannot be known from here, and the detail says why. Never a pass, never a failure
  info        context only

Exit codes: 0 no FAIL (and no WARN with --strict) | 1 FAIL | 2 usage error.

Network: none by default. With --check-branch-protection it runs read-only `gh api`
GET requests, which is the only way to prove the check is required. Everything else is local.
The config is parsed with the lane.py that sits next to this file, so a repo's own copy is
never executed. Stdlib only. Python >= 3.8.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True  # an inspector must not leave files in the repo it inspects
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import lane as lanelib
except Exception:  # missing or broken lane.py is reported by the checks, not raised here
    lanelib = None

VERSION = "0.2.0"
OK, FAIL, WARN, UNVERIFIED, INFO = "verified", "FAIL", "WARN", "unverified", "info"
MAX_FILE_BYTES = 1000000
MAX_TRACKED_FILES = 200000
CRITICAL_SHARE_WARN = 0.30   # heuristic: above this, Critical probably fires too often to be taken seriously
MIN_FILES_FOR_SHARE = 20

# (check name, repo-relative path, status if missing)
REQUIRED_FILES = (
    ("lane-script", "scripts/lane.py", FAIL),
    ("evidence-script", "scripts/evidence_check.py", FAIL),
    ("config", "scripts/lane-config.yaml", FAIL),
    ("ci-template", ".github/workflows/sdlc-gate.yml", FAIL),
    ("pr-template", ".github/pull_request_template.md", WARN),
    ("hook-template", "hooks/pre-push.sh", WARN),
)
TOOLING = ("scripts/lane.py", "scripts/evidence_check.py", "scripts/lane-config.yaml",
           ".github/workflows/sdlc-gate.yml")
GATE_FILES = TOOLING  # what CODEOWNERS should cover
CATCH_ALL = {"**", "*", "**/*", "*/**", "**/**"}
_SHA = re.compile(r"^[0-9a-f]{40}$")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def run(cmd, cwd=None, timeout=20, env=None):
    """Return (returncode, stdout, stderr). 127 if the command cannot run."""
    try:
        proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


def git(root, *args):
    return run(["git", "-C", root] + list(args))


def read_text(path):
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return None
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def sha256(path):
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


def in_git(root):
    code, out, _ = git(root, "rev-parse", "--is-inside-work-tree")
    return code == 0 and out.strip() == "true"


def clip(text, limit=160):
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text if len(text) <= limit else text[:limit - 3] + "..."


# --------------------------------------------------------------------------
# local checks. Each returns a list of (name, status, detail)
# --------------------------------------------------------------------------

def check_environment():
    version = "%d.%d.%d" % sys.version_info[:3]
    if sys.version_info < (3, 8):
        return [("python", FAIL, "Python %s; the gate scripts need >= 3.8" % version)]
    return [("python", OK, "Python %s (>= 3.8)" % version)]


def check_files(root):
    results = []
    for name, rel, missing_status in REQUIRED_FILES:
        present = os.path.isfile(os.path.join(root, rel))
        if present:
            results.append((name, OK, "%s present" % rel))
        else:
            results.append((name, missing_status, "%s missing" % rel))
    return results


def check_drift(root):
    """Compare the repo's scripts with the copies next to doctor.py."""
    results = []
    scripts_dir = os.path.join(root, "scripts")
    if os.path.realpath(scripts_dir) == os.path.realpath(HERE):
        return [("script-drift", OK, "doctor runs from this repo's scripts/, nothing to compare")]
    drifted, compared = [], 0
    for name in ("lane.py", "evidence_check.py"):
        mine, theirs = sha256(os.path.join(HERE, name)), sha256(os.path.join(scripts_dir, name))
        if mine is None or theirs is None:
            continue
        compared += 1
        if mine != theirs:
            drifted.append(name)
    if drifted:
        results.append(("script-drift", WARN,
                        "%s differ from the toolkit copies next to doctor.py (local edits, or a stale install)"
                        % ", ".join(drifted)))
    elif compared:
        results.append(("script-drift", OK, "scripts match the toolkit copies"))
    return results


def load_rules_for(root):
    """Return (rules or None, results). Parses with the trusted lane.py next to this file."""
    path = os.path.join(root, "scripts", "lane-config.yaml")
    if not os.path.isfile(path):
        return None, []  # presence already reported by check_files
    if lanelib is None:
        return None, [("config-valid", UNVERIFIED, "lane.py is not importable next to doctor.py, so the config was not parsed")]
    rules, error = lanelib.load_rules(path)
    if rules is None:
        return None, [("config-valid", FAIL, clip(error))]
    counts = {name: len(rules[name]) for name in lanelib.LANE_SECTIONS}
    detail = "valid (version %d; %d critical, %d standard, %d lite rules)" % (
        lanelib.CONFIG_VERSION, counts["critical"], counts["standard"], counts["lite"])
    results = [("config-valid", OK, detail)]

    if counts["critical"] == 0:
        results.append(("config-critical", WARN,
                        "no Critical rules: only the built-in gate files are Critical, so auth, payments and "
                        "migrations get the same process as everything else"))
    broad = [(name, pattern) for name in ("critical", "lite") for pattern in rules[name] if pattern.strip() in CATCH_ALL]
    for name, pattern in broad:
        meaning = "every path is Critical (alert fatigue)" if name == "critical" else \
            "every path not claimed by a higher lane becomes Lite, which removes the safe default"
        results.append(("config-catch-all", WARN, "%s rule %r: %s" % (name, pattern, meaning)))
    wide = [p for p in rules.get("non_executable", []) if p.strip() in CATCH_ALL or p.strip() in ("*.md", "**/*.md")]
    if wide:
        results.append(("config-non-executable", WARN,
                        "non_executable %s lets changes skip test evidence; wrong if Markdown is behaviour in this repo "
                        "(for example SKILL.md)" % ", ".join(repr(p) for p in wide)))

    # canary: the built-in protection of the gate files must survive any config
    lane_, _ = lanelib.classify(["scripts/lane.py"], rules)
    if lane_ != "Critical":
        results.append(("builtin-protection", FAIL,
                        "scripts/lane.py classified %s, not Critical: the gate no longer protects itself" % lane_))
    else:
        results.append(("builtin-protection", OK, "gate files are always Critical"))
    return rules, results


def check_rule_coverage(root, rules):
    """Calibration: do the rules match real files, and how often is Critical?"""
    if rules is None or lanelib is None:
        return []
    code, out, _ = git(root, "ls-files", "-z")
    if code != 0:
        return [("rule-coverage", UNVERIFIED, "not a git work tree, so rules were not tested against real files")]
    files = [p for p in out.split("\0") if p][:MAX_TRACKED_FILES]
    if not files:
        return [("rule-coverage", UNVERIFIED, "no tracked files yet (commit something, then re-run)")]
    compiled = lanelib.compile_rules(rules)
    config_critical = set(rules["critical"])
    hits = dict.fromkeys(config_critical, 0)
    per_lane = {"Critical": 0, "Standard": 0, "Lite": 0}
    unmatched = total = 0
    for item in files:
        path, _ = lanelib.clean_path(item)
        if path is None:
            continue
        total += 1
        lane_, rule = lanelib.path_lane(path, compiled)
        per_lane[lane_] += 1
        if rule is None:
            unmatched += 1
        for pattern, matches in compiled["critical"]:
            if pattern in config_critical and matches(path):
                hits[pattern] += 1
    results = [("rule-coverage", INFO,
                "%d tracked files: %d Critical, %d Standard, %d Lite (%d matched no rule and default to Standard)"
                % (total, per_lane["Critical"], per_lane["Standard"], per_lane["Lite"], unmatched))]
    dead = sorted(pattern for pattern, count in hits.items() if count == 0)
    if dead:
        results.append(("rule-dead-critical", WARN,
                        "Critical rule(s) matching no tracked file: %s (typo, stale, or not yet calibrated for this repo)"
                        % ", ".join(dead[:5]) + (" +%d more" % (len(dead) - 5) if len(dead) > 5 else "")))
    if total >= MIN_FILES_FOR_SHARE and per_lane["Critical"] / float(total) > CRITICAL_SHARE_WARN:
        results.append(("rule-critical-share", WARN,
                        "%d%% of tracked files are Critical (heuristic limit %d%%): a lane that fires this often gets ignored"
                        % (round(100.0 * per_lane["Critical"] / total), int(CRITICAL_SHARE_WARN * 100))))
    return results


def _strip_yaml_comments(text):
    return re.sub(r"(?m)(^|\s)#.*$", r"\1", text)


def _base_checkout_dir(text):
    """Directory written by the actions/checkout step whose ref is the PR base SHA, or None."""
    steps = re.split(r"(?m)^\s*-\s+(?=\S)", text)
    for step in steps:
        if "actions/checkout@" in step and re.search(r"ref\s*:.*base\.sha", step):
            match = re.search(r"path\s*:\s*([\w./-]+)", step)
            if match:
                return match.group(1).strip("./") or None
    return None


def check_workflow(root):
    path = os.path.join(root, ".github", "workflows", "sdlc-gate.yml")
    if not os.path.isfile(path):
        return []
    raw = read_text(path)
    if raw is None:
        return [("ci-readable", FAIL, "workflow file unreadable or larger than %d bytes" % MAX_FILE_BYTES)]
    text = _strip_yaml_comments(raw)
    results = []

    if re.search(r"\bpull_request_target\b", text):
        results.append(("ci-no-pr-target", FAIL,
                        "uses pull_request_target: it runs with write access and secrets next to untrusted PR code"))
    else:
        results.append(("ci-no-pr-target", OK, "does not use pull_request_target"))

    on_pr = re.search(r"(?m)^(?:on\s*:\s*.*\bpull_request\b|\s{1,4}pull_request\s*:|\s*-\s*pull_request\s*$)", text)
    results.append(("ci-trigger", OK if on_pr else FAIL,
                    "runs on pull_request" if on_pr else "does not trigger on pull_request, so the gate never runs"))
    if on_pr:
        edited = re.search(r"\bedited\b", text)
        results.append(("ci-edited-trigger", OK if edited else WARN,
                        "re-checks when the PR description is edited" if edited else
                        "no 'edited' trigger: evidence lives in the PR description, so edits will not re-run the gate"))

    invokes = re.search(r"evidence_check\.py", text) and re.search(r"--ci\b", text) and re.search(r"--base\b", text)
    results.append(("ci-invokes-gate", OK if invokes else FAIL,
                    "runs evidence_check.py --ci with --base" if invokes else
                    "does not run evidence_check.py with both --ci and --base (the gate needs a computed lane)"))

    depth = re.search(r"fetch-depth\s*:\s*0\b", text)
    results.append(("ci-fetch-depth", OK if depth else FAIL,
                    "full history checked out for the merge-base diff" if depth else
                    "no 'fetch-depth: 0': a shallow clone cannot compute the diff, so every PR errors"))

    trusted_dir = _base_checkout_dir(text)
    trusted = bool(trusted_dir) and re.search(
        r"python3?\s+\.?/?%s/scripts/evidence_check\.py" % re.escape(trusted_dir), text)
    results.append(("ci-trusted-tooling", OK if trusted else WARN,
                    "gate scripts run from the base-branch checkout (%s/)" % trusted_dir if trusted else
                    "gate scripts are not run from a checkout of the base commit: a PR can weaken the gate that judges it"))

    perms = re.search(r"(?m)^\s*permissions\s*:", text) and re.search(r"contents\s*:\s*read", text)
    results.append(("ci-permissions", OK if perms else WARN,
                    "token limited to contents: read" if perms else
                    "no least-privilege 'permissions:' block (the default token may be broader than needed)"))

    checkouts = len(re.findall(r"uses\s*:\s*actions/checkout@", text))
    persisted = len(re.findall(r"persist-credentials\s*:\s*false", text))
    if checkouts:
        results.append(("ci-persist-credentials", OK if persisted >= checkouts else WARN,
                        "checkout credentials not persisted" if persisted >= checkouts else
                        "%d checkout step(s) lack 'persist-credentials: false'" % (checkouts - persisted)))

    unpinned = []
    for action, ref in re.findall(r"(?m)^\s*-?\s*uses\s*:\s*([^\s@]+)@(\S+)", text):
        label = "%s@%s" % (action, ref)
        if not _SHA.match(ref) and label not in unpinned:
            unpinned.append(label)
    if unpinned:
        results.append(("ci-pinned-actions", WARN,
                        "not pinned to a commit SHA: %s%s" % (", ".join(unpinned[:3]),
                                                              " +%d more" % (len(unpinned) - 3) if len(unpinned) > 3 else "")))
    else:
        results.append(("ci-pinned-actions", OK, "all actions pinned to commit SHAs"))
    return results


HOOK_MARKER = "sdlc-pre-push"


def check_hook(root):
    """Is a pre-push hook that git will actually RUN installed, and is it ours?

    Git only runs a file named exactly 'pre-push' (no extension), found in core.hooksPath or
    .git/hooks, so presence of hooks/pre-push.sh proves nothing. Ask git where it will look.
    """
    if not os.path.isfile(os.path.join(root, "hooks", "pre-push.sh")):
        return []
    if not in_git(root):
        return [("hook-active", UNVERIFIED, "not a git work tree")]
    code, out, _ = git(root, "rev-parse", "--git-path", "hooks/pre-push")
    if code != 0 or not out.strip():
        return [("hook-active", UNVERIFIED, "could not ask git where pre-push hooks live")]
    target = out.strip()
    target = target if os.path.isabs(target) else os.path.join(root, target)
    shown = os.path.relpath(target, root)
    if not os.path.isfile(target):
        return [("hook-active", WARN,
                 "git would run %s and nothing is there (git only runs a file named exactly 'pre-push', so hooks/pre-push.sh alone is "
                 "never run). Fix: add hooks/pre-push (the dispatcher) and `git config core.hooksPath hooks`, or copy "
                 "hooks/pre-push.sh to .git/hooks/pre-push" % shown)]
    if not os.access(target, os.X_OK):
        return [("hook-active", WARN, "%s is not executable, so git skips it: chmod +x %s" % (shown, shown))]
    text = read_text(target) or ""
    if HOOK_MARKER not in text:
        return [("hook-active", WARN, "a pre-push hook is active (%s) but it is not the sdlc hook; the lane warning will not run" % shown)]
    return [("hook-active", OK, "git runs %s (advisory only: `git push --no-verify` skips it)" % shown)]


def _codeowners_path(root):
    for rel in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):  # GitHub's lookup order
        if os.path.isfile(os.path.join(root, rel)):
            return rel
    return None


def check_codeowners(root):
    rel = _codeowners_path(root)
    if rel is None:
        return [("codeowners", WARN,
                 "no CODEOWNERS file: nothing requires an owner's review when a PR edits the workflow or scripts")]
    if lanelib is None:
        return [("codeowners", UNVERIFIED, "lane.py not importable, so CODEOWNERS patterns were not evaluated")]
    text = read_text(os.path.join(root, rel)) or ""
    entries = []
    for line in text.splitlines():
        line = re.sub(r"(^|\s)#.*$", "", line).strip()
        if not line:
            continue
        parts = line.split()
        try:
            entries.append((lanelib.compile_pattern(parts[0]), len(parts) > 1))
        except lanelib.ConfigError:
            continue
    uncovered = []
    for target in GATE_FILES:
        covered = False
        for matches, has_owner in entries:  # last matching pattern wins, and an owner-less line un-owns the path
            if matches(target):
                covered = has_owner
        if not covered:
            uncovered.append(target)
    if uncovered:
        return [("codeowners", WARN, "%s: gate files with no code owner: %s" % (rel, ", ".join(uncovered)))]
    return [("codeowners", OK, "%s covers the gate files. Whether review is REQUIRED is a branch-protection "
                               "setting (see --check-branch-protection)" % rel)]


def check_default_branch(root):
    if not in_git(root):
        return [("tooling-on-default-branch", UNVERIFIED, "not a git work tree")]
    results = []
    code, out, _ = git(root, "status", "--porcelain", "--", "scripts", ".github", "hooks")
    pending = [ln for ln in out.splitlines() if ln.strip() and "__pycache__" not in ln and not ln.endswith(".pyc")] \
        if code == 0 else []
    if pending:
        results.append(("gate-files-committed", WARN,
                        "%d uncommitted change(s) under scripts/, .github/ or hooks/: the gate only reads COMMITTED "
                        "tooling from the base branch" % len(pending)))
    code, out, _ = git(root, "symbolic-ref", "-q", "refs/remotes/origin/HEAD")
    if code != 0 or not out.strip():
        results.append(("tooling-on-default-branch", UNVERIFIED,
                        "origin/HEAD is unknown; run `git remote set-head origin -a` and re-run"))
        return results
    ref = out.strip().replace("refs/remotes/", "", 1)
    missing = [rel for rel in TOOLING if git(root, "cat-file", "-e", "%s:%s" % (ref, rel))[0] != 0]
    if missing:
        results.append(("tooling-on-default-branch", WARN,
                        "missing on %s (as of the last fetch): %s. The gate reads its tooling from the base branch, so "
                        "PRs error until it is merged there" % (ref, ", ".join(missing))))
    else:
        results.append(("tooling-on-default-branch", OK, "present on %s (as of the last fetch)" % ref))
    return results


def check_shallow(root):
    if not in_git(root):
        return []
    code, out, _ = git(root, "rev-parse", "--is-shallow-repository")
    if code == 0 and out.strip() == "true":
        return [("shallow-clone", WARN, "this is a shallow clone: `lane.py --base` and the merge-base diff can fail here")]
    return []


# --------------------------------------------------------------------------
# opt-in remote check (read-only `gh api` GETs)
# --------------------------------------------------------------------------

_REMOTE = re.compile(r"^(?:https://(?:[^@/]+@)?github\.com/|git@github\.com:|ssh://git@github\.com/)"
                     r"([^/\s]+)/([^/\s]+?)(?:\.git)?/?$")


def _gh(path):
    env = dict(os.environ, GH_PROMPT_DISABLED="1", GH_NO_UPDATE_NOTIFIER="1")
    code, out, err = run(["gh", "api", path], env=env)
    if code == 0:
        try:
            return "ok", json.loads(out), ""
        except ValueError:
            return "error", None, "unparseable response"
    return "error", None, clip(err or out or "gh api failed", 120)


def _context_matches(context, check_name):
    return context == check_name or context.endswith("/ " + check_name)


def check_branch_protection(root, check_name):
    name = "required-check"
    if not in_git(root):
        return [(name, UNVERIFIED, "not a git work tree")]
    code, out, _ = git(root, "remote", "get-url", "origin")
    match = _REMOTE.match(out.strip()) if code == 0 else None
    if not match:
        return [(name, UNVERIFIED, "origin is not a github.com remote, so branch protection cannot be read")]
    slug = "%s/%s" % match.groups()
    if shutil.which("gh") is None:
        return [(name, UNVERIFIED, "gh CLI not found; install it and run `gh auth login`, or check branch protection by hand")]
    state, repo, err = _gh("repos/%s" % slug)
    if state != "ok" or not isinstance(repo, dict) or not repo.get("default_branch"):
        return [(name, UNVERIFIED, "could not read the repository (%s)" % (err or "no default branch in response"))]
    branch = repo["default_branch"]

    matched, unpinned, answered, errors = False, False, 0, []
    owners_required, owners_known, admins_enforced = False, False, None

    state, rules, err = _gh("repos/%s/rules/branches/%s" % (slug, branch))
    if state == "ok" and isinstance(rules, list):
        answered += 1
        for rule in rules:
            params = rule.get("parameters") or {}
            if rule.get("type") == "required_status_checks":
                for item in params.get("required_status_checks") or []:
                    if _context_matches(str(item.get("context", "")), check_name):
                        matched = True
                        if item.get("integration_id") in (None, 0, -1):
                            unpinned = True
            if rule.get("type") == "pull_request":
                owners_known = True
                owners_required = owners_required or bool(params.get("require_code_owner_review"))
    else:
        errors.append("rulesets: %s" % (err or "unexpected response"))

    state, prot, err = _gh("repos/%s/branches/%s/protection" % (slug, branch))
    if state == "ok" and isinstance(prot, dict):
        answered += 1
        required = prot.get("required_status_checks") or {}
        for item in required.get("checks") or []:
            if _context_matches(str(item.get("context", "")), check_name):
                matched = True
                if item.get("app_id") in (None, 0, -1):
                    unpinned = True
        for context in required.get("contexts") or []:
            if _context_matches(str(context), check_name) and not matched:
                matched, unpinned = True, True
        reviews = prot.get("required_pull_request_reviews")
        if isinstance(reviews, dict):
            owners_known = True
            owners_required = owners_required or bool(reviews.get("require_code_owner_reviews"))
        admins_enforced = (prot.get("enforce_admins") or {}).get("enabled")
    elif "not protected" in err.lower():
        answered += 1  # an authoritative "no classic protection"
    else:
        errors.append("branch protection: %s" % (err or "unexpected response"))

    results = []
    if matched:
        results.append((name, OK, "'%s' is a required status check on %s" % (check_name, branch)))
        if unpinned:
            results.append(("required-check-source", WARN,
                            "the required check is not pinned to the GitHub Actions app: any other app or status "
                            "using the name '%s' could satisfy it" % check_name))
    elif not errors:  # both sources answered authoritatively and neither lists the check
        results.append((name, FAIL, "'%s' is NOT a required status check on %s: the gate cannot block merges" % (check_name, branch)))
    else:
        results.append((name, UNVERIFIED, "could not read everything (%s); not proven either way" % "; ".join(errors)))

    if owners_known and answered:
        results.append(("codeowners-required", OK if owners_required else WARN,
                        "code-owner review is required on %s" % branch if owners_required else
                        "code-owner review is not required on %s: CODEOWNERS entries are advisory" % branch))
    if admins_enforced is False:
        results.append(("admins-bound", WARN, "branch protection does not apply to admins: they can merge past the gate"))
    return results


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------

def check_repo(root, check_remote=False, check_name="evidence"):
    """Return a list of (name, status, detail)."""
    results = check_environment()
    results += check_files(root)
    results += check_drift(root)
    rules, config_results = load_rules_for(root)
    results += config_results
    results += check_rule_coverage(root, rules)
    results += check_workflow(root)
    results += check_hook(root)
    results += check_codeowners(root)
    results += check_default_branch(root)
    results += check_shallow(root)
    if check_remote:
        results += check_branch_protection(root, check_name)
    else:
        results.append(("required-check", UNVERIFIED,
                        "mark the CI check '%s' as required in branch protection or a ruleset; nothing blocks merges until "
                        "then. Prove it with --check-branch-protection (uses gh)" % check_name))
    return results


def summarise(results):
    counts = {OK: 0, FAIL: 0, WARN: 0, UNVERIFIED: 0, INFO: 0}
    for _, status, _ in results:
        counts[status] += 1
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check install health")
    parser.add_argument("--root", default=".")
    parser.add_argument("--strict", action="store_true", help="treat WARN as failure")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check-branch-protection", action="store_true",
                        help="read branch protection via `gh api` (network, read-only)")
    parser.add_argument("--check-name", default="evidence",
                        help="job name of the required check (default: evidence)")
    args = parser.parse_args(argv)
    if not os.path.isdir(args.root):
        sys.stderr.write("doctor: --root %r is not a directory\n" % args.root)
        return 2

    results = check_repo(args.root, args.check_branch_protection, args.check_name)
    counts = summarise(results)
    failed = counts[FAIL] > 0 or (args.strict and counts[WARN] > 0)
    if args.json:
        print(json.dumps({"version": VERSION, "summary": counts, "failed": failed,
                          "results": [{"name": n, "status": s, "detail": d} for n, s, d in results]}, sort_keys=True))
    else:
        print("doctor %s" % VERSION)
        for name, status, detail in results:
            print("%s: %s - %s" % (name, status, detail))
        print("summary: %d verified, %d FAIL, %d WARN, %d unverified" % (
            counts[OK], counts[FAIL], counts[WARN], counts[UNVERIFIED]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
