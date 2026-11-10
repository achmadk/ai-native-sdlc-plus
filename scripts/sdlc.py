"""Unified front-door CLI over the SDLC gate, validators, doctor, and lifecycle.

Dispatches strictly to helpers and resources inside this trusted runtime tree.
Never imports or executes Python modules from an inspected target repository or CWD.
Python >= 3.8; standard library only.
"""

import sys

if sys.version_info < (3, 8):
    sys.exit("sdlc requires Python >= 3.8")
sys.dont_write_bytecode = True

import argparse
import importlib.util
import json
import os
import shlex


HERE = os.path.dirname(os.path.abspath(__file__))
RUNTIME_ROOT = os.path.dirname(HERE)

SUPPORTED_COMMANDS = ("init", "lane", "lite", "check", "doctor", "update", "uninstall", "status", "explain")
CHECK_SUBCOMMANDS = ("spec", "brief", "evidence")

# Fixed helper mapping inside RUNTIME_ROOT: (entry_relpath, required_companion_relpaths)
DELEGATED_HELPERS = {
    ("lane",): (
        "scripts/lane.py",
        ("scripts/lane.py", "scripts/lane-config.yaml"),
    ),
    ("lite",): (
        "scripts/lite.py",
        ("scripts/lite.py", "scripts/lane.py", "scripts/lane-config.yaml", "scripts/evidence_check.py"),
    ),
    ("check", "spec"): (
        "skills/spec-first/scripts/check_spec.py",
        ("scripts/check_spec.py", "skills/spec-first/scripts/check_spec.py"),
    ),
    ("check", "brief"): (
        "skills/context-pack/scripts/check_brief.py",
        ("scripts/check_brief.py", "skills/context-pack/scripts/check_brief.py"),
    ),
    ("check", "evidence"): (
        "scripts/evidence_check.py",
        ("scripts/evidence_check.py", "scripts/lane.py", "scripts/lane-config.yaml"),
    ),
}

TOP_HELP = """\
usage: sdlc <command> [options]

Supported commands:
  init        Initialize the owned SDLC runtime, user policy starter, and selected agent profiles
  lane        Classify changed paths into Lite, Standard, or Critical
  lite        Draft and verify a factual PR description for an eligible Lite change
  check       Run a policy validator: check spec | check brief | check evidence
  doctor      Inspect installation health with actionable grouped findings
  status      Inspect owned runtime state and drift without modifying files
  update      Reconcile recognized unchanged owned files to this distribution
  uninstall   Remove eligible unchanged owned files while preserving user policy
  explain     Explain a check ID and its safe next step without modifying files

Integration entry point:
  sdlc check evidence ...   (or: python3 <tool-root>/scripts/sdlc.py check evidence ...)
  Note: 'gate' is not a supported alias (use 'sdlc check evidence ...').

Run 'sdlc <command> --help' (or 'sdlc check <subcommand> --help') for command options.
"""

CHECK_HELP = """\
usage: sdlc check <spec|brief|evidence> [options]

Supported check subcommands:
  spec        Validate a spec or Critical intent document (delegates to check_spec.py)
  brief       Validate a context-pack brief (delegates to check_brief.py)
  evidence    Verify lane evidence locally or in --ci mode (delegates to evidence_check.py)

Run 'sdlc check <subcommand> --help' for native validator options.
"""


class RuntimeIntegrityError(Exception):
    """Raised when the invoked runtime distribution is incomplete or unsafe."""


def _scrub_import_paths(extra_untrusted=()):
    cwd = os.path.realpath(os.getcwd())
    blocked = {cwd}
    for item in extra_untrusted:
        if item:
            blocked.add(os.path.realpath(item))
    cleaned = []
    for entry in sys.path:
        if entry in ("", "."):
            continue
        resolved = os.path.realpath(entry)
        if resolved in blocked:
            continue
        cleaned.append(entry)
    sys.path[:] = cleaned


def resolve_runtime_file(runtime_root, relpath):
    root_real = os.path.realpath(runtime_root)
    full = os.path.join(runtime_root, *relpath.split("/"))
    try:
        info = os.lstat(full)
    except OSError:
        raise RuntimeIntegrityError("missing required runtime component: %s" % relpath)
    if os.path.islink(full):
        raise RuntimeIntegrityError("refusing symlinked runtime component: %s" % relpath)
    full_real = os.path.realpath(full)
    try:
        inside = os.path.commonpath([root_real, full_real]) == root_real
    except ValueError:
        inside = False
    if not inside or not os.path.isfile(full_real):
        raise RuntimeIntegrityError("invalid runtime component: %s" % relpath)
    return full_real


def load_runtime_module(runtime_root, module_name, relpath, required=()):
    for req in required:
        resolve_runtime_file(runtime_root, req)
    target = resolve_runtime_file(runtime_root, relpath)
    spec = importlib.util.spec_from_file_location(module_name, target)
    if spec is None or spec.loader is None:
        raise RuntimeIntegrityError("cannot load runtime component: %s" % relpath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _invoke_helper_main(module, prog, forwarded):
    saved_argv = sys.argv[:]
    try:
        sys.argv = [prog] + list(forwarded)
        try:
            code = module.main(list(forwarded))
        except SystemExit as exc:
            if exc.code is None:
                return 0
            if isinstance(exc.code, int):
                return exc.code
            sys.stderr.write(str(exc.code) + "\n")
            return 1
        return 0 if code is None else int(code)
    finally:
        sys.argv = saved_argv


def _usage_error(message):
    sys.stderr.write("sdlc: %s\n" % message)
    sys.stderr.write("supported commands: %s\n" % ", ".join(SUPPORTED_COMMANDS))
    sys.stderr.write("run 'sdlc --help' for usage.\n")
    return 2


def _build_doctor_parser():
    parser = argparse.ArgumentParser(
        prog="sdlc doctor",
        description="Inspect repository health with grouped actionable findings (retains raw doctor checks)",
    )
    parser.add_argument("--root", default=".", help="repository root to inspect (default: .)")
    parser.add_argument("--strict", action="store_true", help="treat WARN findings as blocking failures")
    parser.add_argument("--json", action="store_true", help="emit structured JSON with raw results and action groups")
    parser.add_argument("--raw", action="store_true", help="emit legacy line-per-check doctor output")
    parser.add_argument("--check-branch-protection", action="store_true",
                        help="read branch protection via `gh api` (network, read-only)")
    parser.add_argument("--require-enforcement", action="store_true",
                        help="require the complete supported hosted profile; needs --check-branch-protection")
    parser.add_argument("--check-name", default="evidence",
                        help="job name of the required check (default: evidence)")
    return parser


def _build_explain_parser():
    parser = argparse.ArgumentParser(
        prog="sdlc explain",
        description="Explain a doctor check ID or family and its safe next action (never mutates files)",
    )
    parser.add_argument("check_id", help="check identifier (for example: codeowners, hook-active, enforcement-readiness)")
    parser.add_argument("--root", default=".", help="target repository root used to format exact next commands")
    parser.add_argument("--json", action="store_true", help="emit machine-readable explanation")
    return parser


def _build_init_parser():
    parser = argparse.ArgumentParser(
        prog="sdlc init",
        description="Initialize the owned SDLC runtime, canonical AGENTS.md starter, and selected native agent profiles",
    )
    parser.add_argument("--root", default=".", help="destination project directory (default: .)")
    parser.add_argument("--agents", default=None,
                        help="comma-separated profiles: claude,cursor,copilot,codex,gemini,opencode,kilo")
    parser.add_argument("--dry-run", action="store_true", help="plan operations without creating or modifying files")
    parser.add_argument("--json", action="store_true", help="emit structured JSON plan/result")
    return parser


def _build_status_parser():
    parser = argparse.ArgumentParser(
        prog="sdlc status",
        description="Read-only inspection of owned installation state, canonical policy, and drift",
    )
    parser.add_argument("--root", default=".", help="project directory to inspect (default: .)")
    parser.add_argument("--json", action="store_true", help="emit structured JSON status")
    return parser


def _build_update_parser():
    parser = argparse.ArgumentParser(
        prog="sdlc update",
        description="Reconcile recognized unchanged owned files to this trusted distribution",
    )
    parser.add_argument("--root", default=".", help="project directory to update (default: .)")
    parser.add_argument("--dry-run", action="store_true", help="plan updates without modifying files")
    parser.add_argument("--json", action="store_true", help="emit structured JSON plan/result")
    return parser


def _build_uninstall_parser():
    parser = argparse.ArgumentParser(
        prog="sdlc uninstall",
        description="Remove eligible unchanged owned files while preserving AGENTS.md and unowned content",
    )
    parser.add_argument("--root", default=".", help="project directory to uninstall from (default: .)")
    parser.add_argument("--dry-run", action="store_true", help="plan removals without modifying files")
    parser.add_argument("--json", action="store_true", help="emit structured JSON plan/result")
    return parser


def _parse_with_exit(parser, argv):
    try:
        return parser.parse_args(argv), None
    except SystemExit as exc:
        code = 0 if exc.code is None else (exc.code if isinstance(exc.code, int) else 2)
        return None, code


def _extract_target_roots(args):
    roots = []
    for idx, token in enumerate(args):
        if token in ("--root", "--repo-root") and idx + 1 < len(args):
            roots.append(args[idx + 1])
        elif token.startswith("--root="):
            roots.append(token.split("=", 1)[1])
        elif token.startswith("--repo-root="):
            roots.append(token.split("=", 1)[1])
    return roots


def dispatch(argv=None, runtime_root=None):
    args = list(sys.argv[1:] if argv is None else argv)
    rt_root = os.path.abspath(runtime_root or RUNTIME_ROOT)
    target_roots = _extract_target_roots(args)
    extra_blocked = []
    for item in target_roots:
        extra_blocked.append(item)
        extra_blocked.append(os.path.join(item, "scripts"))
    _scrub_import_paths(extra_blocked)

    if not args:
        return _usage_error("missing command")
    if args[0] in ("-h", "--help"):
        sys.stdout.write(TOP_HELP)
        return 0

    cmd = args[0]
    rest = args[1:]
    if cmd not in SUPPORTED_COMMANDS:
        if cmd == "gate":
            return _usage_error("unknown command 'gate' (use 'sdlc check evidence ...')")
        return _usage_error("unknown command %r" % cmd)

    try:
        if cmd == "lane":
            relpath, required = DELEGATED_HELPERS[("lane",)]
            mod = load_runtime_module(rt_root, "_sdlc_delegated_lane", relpath, required)
            return _invoke_helper_main(mod, "sdlc lane", rest)

        if cmd == "lite":
            relpath, required = DELEGATED_HELPERS[("lite",)]
            mod = load_runtime_module(rt_root, "_sdlc_delegated_lite", relpath, required)
            return _invoke_helper_main(mod, "sdlc lite", rest)

        if cmd == "check":
            if not rest:
                sys.stderr.write("sdlc check: missing check subcommand (choose from: %s)\n"
                                 % ", ".join(CHECK_SUBCOMMANDS))
                sys.stderr.write("usage: sdlc check <spec|brief|evidence> [options]\n")
                return 2
            if rest[0] in ("-h", "--help"):
                sys.stdout.write(CHECK_HELP)
                return 0
            sub = rest[0]
            sub_rest = rest[1:]
            if sub not in CHECK_SUBCOMMANDS:
                sys.stderr.write("sdlc check: unknown check subcommand %r (choose from: %s)\n"
                                 % (sub, ", ".join(CHECK_SUBCOMMANDS)))
                sys.stderr.write("usage: sdlc check <spec|brief|evidence> [options]\n")
                return 2
            relpath, required = DELEGATED_HELPERS[("check", sub)]
            mod = load_runtime_module(rt_root, "_sdlc_delegated_check_" + sub, relpath, required)
            return _invoke_helper_main(mod, "sdlc check " + sub, sub_rest)

        if cmd == "doctor":
            parsed, exit_code = _parse_with_exit(_build_doctor_parser(), rest)
            if exit_code is not None:
                return exit_code
            return _run_doctor(rt_root, parsed)

        if cmd == "explain":
            parsed, exit_code = _parse_with_exit(_build_explain_parser(), rest)
            if exit_code is not None:
                return exit_code
            return _run_explain(rt_root, parsed)

        if cmd == "init":
            parsed, exit_code = _parse_with_exit(_build_init_parser(), rest)
            if exit_code is not None:
                return exit_code
            return _run_lifecycle(rt_root, "init", parsed)

        if cmd == "status":
            parsed, exit_code = _parse_with_exit(_build_status_parser(), rest)
            if exit_code is not None:
                return exit_code
            return _run_lifecycle(rt_root, "status", parsed)

        if cmd == "update":
            parsed, exit_code = _parse_with_exit(_build_update_parser(), rest)
            if exit_code is not None:
                return exit_code
            return _run_lifecycle(rt_root, "update", parsed)

        if cmd == "uninstall":
            parsed, exit_code = _parse_with_exit(_build_uninstall_parser(), rest)
            if exit_code is not None:
                return exit_code
            return _run_lifecycle(rt_root, "uninstall", parsed)

    except RuntimeIntegrityError as exc:
        sys.stderr.write("sdlc: %s\n" % exc)
        return 3

    return _usage_error("unhandled command %r" % cmd)


_KNOWN_CI_CHECKS = frozenset(
    "ci-" + suffix
    for suffix in (
        "workflow-profile",
        "no-pr-target",
        "trigger",
        "edited-trigger",
        "invokes-gate",
        "fetch-depth",
        "trusted-tooling",
        "isolated-python",
        "permissions",
        "persist-credentials",
        "pinned-actions",
    )
)

_KNOWN_SCANNER_CHECKS = frozenset(
    "scanner-" + suffix
    for suffix in (
        "profile-data",
        "workflow-profile",
        "no-pr-target",
        "trigger",
        "invokes-gate",
        "fetch-depth",
        "permissions",
        "persist-credentials",
        "pinned-actions",
    )
)

_KNOWN_ENFORCEMENT_CHECKS = frozenset(
    "enforcement-" + suffix
    for suffix in (
        "readiness",
        "inspection",
        "application",
        "protection-sources",
        "merge-queue",
        "check-evidence",
        "check-gitleaks",
        "pr",
        "owner-review",
        "review-freshness",
        "branch-freshness",
        "bypass",
        "snapshot",
        "tooling",
        "workflow-evidence",
        "workflow-gitleaks",
        "workflow-names",
        "ownership",
    )
)


def _format_command(argv):
    return " ".join(shlex.quote(str(part)) for part in argv)


def lookup_check_catalog(check_id, root_arg="."):
    """Return trusted remediation/explanation metadata for a known check ID, or None."""
    root_str = str(root_arg)

    if check_id == "python":
        argv = ["python3", "--version"]
        return {
            "check_id": check_id,
            "family": "python-runtime",
            "group_id": "python-runtime",
            "title": "Run SDLC tooling on Python >= 3.8",
            "optional_non_strict": False,
            "command_kind": "inspection",
            "group_argv": argv,
            "explain_argv": argv,
            "evidence": "Inspects sys.version_info of the Python interpreter executing doctor.",
            "limitation": "Confirms local interpreter version only; does not verify CI runner images or hosted settings.",
        }

    if check_id in ("lane-script", "evidence-script", "config", "ci-template", "pr-template", "hook-template"):
        argv = ["sdlc", "init", "--root", root_str]
        return {
            "check_id": check_id,
            "family": "owned-runtime-files",
            "group_id": "install-missing-files",
            "title": "Initialize or restore missing owned SDLC runtime and template files",
            "optional_non_strict": False,
            "command_kind": "remediation",
            "group_argv": argv,
            "explain_argv": argv,
            "evidence": "Checks whether the required SDLC script, config, workflow, PR template, or hook file exists under the target repository.",
            "limitation": "File presence alone does not prove byte integrity, git commit status on the base branch, or hosted merge enforcement.",
        }

    if check_id == "script-drift":
        argv = ["sdlc", "status", "--root", root_str]
        return {
            "check_id": check_id,
            "family": "runtime-drift",
            "group_id": "reconcile-script-drift",
            "title": "Inspect script drift before reconciling with sdlc update",
            "optional_non_strict": False,
            "command_kind": "inspection",
            "group_argv": argv,
            "explain_argv": argv,
            "evidence": "Compares SHA-256 digests of target scripts/lane.py and scripts/evidence_check.py against the invoked toolkit runtime.",
            "limitation": "Distinguishes matching vs differing bytes; run 'sdlc status' to check whether differences are stale owned files or local edits.",
        }

    if check_id in ("config-valid", "config-critical", "config-catch-all", "config-non-executable"):
        return {
            "check_id": check_id,
            "family": "lane-config",
            "group_id": "calibrate-lane-config",
            "title": "Review and calibrate scripts/lane-config.yaml risk boundaries",
            "optional_non_strict": False,
            "command_kind": "discovery",
            "group_argv": ["sdlc", "explain", check_id, "--root", root_str],
            "explain_argv": ["sdlc", "doctor", "--root", root_str],
            "evidence": "Parses scripts/lane-config.yaml with trusted lane.py and checks for syntax errors, missing Critical patterns, catch-all globs, or overly broad non_executable exemptions.",
            "limitation": "Cannot decide which domain paths in your codebase handle auth, money, or migrations; human architecture review is required.",
        }

    if check_id == "builtin-protection":
        argv = ["sdlc", "status", "--root", root_str]
        return {
            "check_id": check_id,
            "family": "builtin-protection",
            "group_id": "restore-builtin-protection",
            "title": "Restore non-overridable built-in Critical gate protection",
            "optional_non_strict": False,
            "command_kind": "inspection",
            "group_argv": argv,
            "explain_argv": argv,
            "evidence": "Verifies that scripts/lane.py still classifies gate control paths as Critical regardless of lane-config.yaml.",
            "limitation": "Confirms classifier self-protection locally; hosted branch protection still governs whether unreviewed PRs can merge.",
        }

    if check_id == "rule-coverage":
        return {
            "check_id": check_id,
            "family": "lane-calibration",
            "group_id": "rule-coverage-summary",
            "title": "Tracked file distribution across Critical, Standard, and Lite lanes",
            "optional_non_strict": False,
            "command_kind": "inspection",
            "group_argv": ["sdlc", "doctor", "--root", root_str],
            "explain_argv": ["sdlc", "doctor", "--root", root_str],
            "evidence": "Classifies git-tracked files against scripts/lane-config.yaml and summarizes Critical, Standard, and Lite counts.",
            "limitation": "Informational distribution over current tracked files; does not validate future untracked paths or runtime behavior.",
        }

    if check_id in ("rule-dead-critical", "rule-critical-share"):
        return {
            "check_id": check_id,
            "family": "lane-calibration",
            "group_id": "optional-rule-calibration",
            "title": "Optional: calibrate starter Critical patterns in scripts/lane-config.yaml",
            "optional_non_strict": True,
            "command_kind": "discovery",
            "group_argv": ["sdlc", "explain", check_id, "--root", root_str],
            "explain_argv": ["sdlc", "doctor", "--root", root_str],
            "evidence": "Checks whether configured Critical globs match zero tracked files or exceed the 30% Critical-share heuristic.",
            "limitation": "Advisory calibration heuristic only: starter Critical globs (such as migrations/** or auth/**) often match zero files in a young repository until those paths exist.",
        }

    if check_id == "hook-active":
        return {
            "check_id": check_id,
            "family": "local-hook",
            "group_id": "optional-local-hook",
            "title": "Optional: enable local advisory pre-push hook (git config core.hooksPath hooks)",
            "optional_non_strict": True,
            "command_kind": "discovery",
            "group_argv": ["sdlc", "explain", "hook-active", "--root", root_str],
            "explain_argv": ["git", "-C", root_str, "config", "core.hooksPath", "hooks"],
            "evidence": "Queries git rev-parse --git-path hooks/pre-push and checks whether an executable SDLC pre-push hook is active in this clone.",
            "limitation": "Local hooks are optional developer advisories (bypassed by git push --no-verify) and are never activated automatically by init; CI + branch protection is the real enforcement boundary.",
        }

    if check_id == "codeowners":
        return {
            "check_id": check_id,
            "family": "codeowners",
            "group_id": "define-codeowners",
            "title": "Create CODEOWNERS assigning human owners to SDLC gate and Critical paths",
            "optional_non_strict": False,
            "command_kind": "discovery",
            "group_argv": ["sdlc", "explain", "codeowners", "--root", root_str],
            "explain_argv": ["sdlc", "doctor", "--root", root_str],
            "evidence": "Inspects .github/CODEOWNERS, CODEOWNERS, or docs/CODEOWNERS to verify owner patterns cover core SDLC gate files.",
            "limitation": "Choosing valid @user or @org/team handles requires human organizational input, and local CODEOWNERS presence does not enable required code-owner review in hosted repository settings.",
        }

    if check_id in ("gate-files-committed", "tooling-on-default-branch"):
        return {
            "check_id": check_id,
            "family": "default-branch-bootstrap",
            "group_id": "bootstrap-default-branch",
            "title": "Commit SDLC gate files and merge/push them to the default branch",
            "optional_non_strict": False,
            "command_kind": "discovery",
            "group_argv": ["sdlc", "explain", "gate-files-committed", "--root", root_str],
            "explain_argv": ["git", "-C", root_str, "status", "--short", "--", "scripts", ".github", "hooks"],
            "evidence": "Checks git status under scripts/, .github/, and hooks/ for uncommitted changes and checks whether core gate tooling exists on refs/remotes/origin/HEAD.",
            "limitation": "Local git only sees the last fetched origin/HEAD ref; the CI gate reads trusted tooling from the hosted base branch once committed and pushed.",
        }

    if check_id == "shallow-clone":
        argv = ["git", "-C", root_str, "fetch", "--unshallow"]
        return {
            "check_id": check_id,
            "family": "git-history",
            "group_id": "fetch-full-history",
            "title": "Unshallow repository history so merge-base lane diffs succeed",
            "optional_non_strict": False,
            "command_kind": "remediation",
            "group_argv": argv,
            "explain_argv": argv,
            "evidence": "Checks git rev-parse --is-shallow-repository.",
            "limitation": "Shallow clones can lack the merge-base commit required for accurate branch diff classification.",
        }

    if check_id in _KNOWN_CI_CHECKS:
        return {
            "check_id": check_id,
            "family": "ci-workflow",
            "group_id": "repair-ci-workflow",
            "title": "Align .github/workflows/sdlc-gate.yml with the isolated read-only gate profile",
            "optional_non_strict": False,
            "command_kind": "discovery",
            "group_argv": ["sdlc", "explain", check_id, "--root", root_str],
            "explain_argv": ["sdlc", "status", "--root", root_str],
            "evidence": "Parses .github/workflows/sdlc-gate.yml as bounded YAML data to check PR triggers, read-only permissions, SHA-pinned actions, persist-credentials: false, base/head checkouts, and python3 -I gate invocation.",
            "limitation": "Static workflow validation proves file structure only; it does not prove GitHub Actions ran the workflow or enforces it on merges.",
        }

    if check_id in _KNOWN_SCANNER_CHECKS:
        return {
            "check_id": check_id,
            "family": "scanner-workflow",
            "group_id": "repair-scanner-workflow",
            "title": "Align .github/workflows/gitleaks.yml with trusted scanner-profiles.json",
            "optional_non_strict": False,
            "command_kind": "discovery",
            "group_argv": ["sdlc", "explain", check_id, "--root", root_str],
            "explain_argv": ["sdlc", "status", "--root", root_str],
            "evidence": "Parses .github/workflows/gitleaks.yml and checks pinned gitleaks action commit SHAs against trusted scripts/scanner-profiles.json.",
            "limitation": "Static workflow validation does not prove GITLEAKS_LICENSE availability, fork scan behavior, or hosted scan execution.",
        }

    if check_id in ("required-check", "required-check-source", "codeowners-required", "admins-bound") or (
        check_id in _KNOWN_ENFORCEMENT_CHECKS
    ):
        inspect_argv = [
            "sdlc",
            "doctor",
            "--root",
            root_str,
            "--check-branch-protection",
            "--require-enforcement",
        ]
        return {
            "check_id": check_id,
            "family": "hosted-enforcement",
            "group_id": "activate-hosted-enforcement",
            "title": "Configure hosted branch/ruleset protection and verify via opt-in gh inspection",
            "optional_non_strict": False,
            "command_kind": "discovery",
            "group_argv": ["sdlc", "explain", check_id, "--root", root_str],
            "explain_argv": inspect_argv,
            "evidence": "Offline runs report hosted enforcement as unverified; opt-in --check-branch-protection --require-enforcement reads GitHub rulesets, classic branch protection, Actions app identity, merge-queue state, and hosted branch blobs via gh api.",
            "limitation": "Local tools never change GitHub settings, and even an observed hosted profile is a point-in-time settings snapshot rather than proof of code correctness, review quality, or runtime agent isolation.",
        }

    return None


def group_doctor_results(results, root_arg=".", strict=False):
    """Group raw (name, status, detail) doctor tuples without dropping any non-verified finding."""
    root_str = str(root_arg)
    buckets = {"blocking": [], "needs_human": [], "informational": []}
    index_by_bucket = {"blocking": {}, "needs_human": {}, "informational": {}}

    for name, status, detail in results:
        if status == "verified":
            continue
        meta = lookup_check_catalog(name, root_arg=root_str)
        if meta is None:
            meta = {
                "group_id": "unknown:" + name,
                "title": "Unrecognized doctor check %r (inspect raw detail)" % name,
                "optional_non_strict": False,
                "command_kind": "inspection",
                "group_argv": ["sdlc", "doctor", "--root", root_str, "--raw"],
            }

        if status == "FAIL" or (strict and status == "WARN") or status not in ("FAIL", "WARN", "unverified", "info"):
            bucket = "blocking"
            optional = False
        elif status == "info":
            bucket = "informational"
            optional = False
        elif not strict and meta["optional_non_strict"] and status in ("WARN", "unverified"):
            bucket = "informational"
            optional = True
        else:
            bucket = "needs_human"
            optional = False

        group_id = meta["group_id"]
        if group_id not in index_by_bucket[bucket]:
            argv = list(meta["group_argv"])
            entry = {
                "group_id": group_id,
                "title": meta["title"],
                "optional": optional,
                "command_kind": meta["command_kind"],
                "next_command_argv": argv,
                "next_command": _format_command(argv),
                "findings": [],
            }
            index_by_bucket[bucket][group_id] = entry
            buckets[bucket].append(entry)
        index_by_bucket[bucket][group_id]["findings"].append(
            {"name": name, "status": status, "detail": detail}
        )

    return buckets


def _run_doctor(rt_root, parsed):
    if parsed.require_enforcement and not parsed.check_branch_protection:
        sys.stderr.write("sdlc doctor: --require-enforcement requires --check-branch-protection\n")
        return 2
    if parsed.require_enforcement and parsed.check_name != "evidence":
        sys.stderr.write(
            "sdlc doctor: --require-enforcement requires the exact evidence and gitleaks checks, not a custom --check-name\n"
        )
        return 2
    if not os.path.isdir(parsed.root):
        sys.stderr.write("sdlc doctor: --root %r is not a directory\n" % parsed.root)
        return 2

    doctor_mod = load_runtime_module(
        rt_root,
        "_sdlc_delegated_doctor",
        "scripts/doctor.py",
        ("scripts/doctor.py", "scripts/lane.py", "scripts/scanner-profiles.json"),
    )
    results = doctor_mod.check_repo(
        parsed.root,
        parsed.check_branch_protection,
        parsed.check_name,
        parsed.require_enforcement,
    )
    counts = doctor_mod.summarise(results)
    failed = counts[doctor_mod.FAIL] > 0 or (parsed.strict and counts[doctor_mod.WARN] > 0)
    groups = group_doctor_results(results, root_arg=parsed.root, strict=parsed.strict)
    action_counts = {key: len(groups[key]) for key in ("blocking", "needs_human", "informational")}

    if parsed.json:
        payload = {
            "version": doctor_mod.VERSION,
            "summary": counts,
            "action_counts": action_counts,
            "failed": failed,
            "groups": groups,
            "results": [{"name": n, "status": s, "detail": d} for n, s, d in results],
        }
        print(json.dumps(payload, sort_keys=True))
        return 1 if failed else 0

    if parsed.raw:
        print("doctor %s" % doctor_mod.VERSION)
        for name, status, detail in results:
            print("%s: %s - %s" % (name, status, detail))
        print(
            "summary: %d verified, %d FAIL, %d WARN, %d unverified"
            % (
                counts[doctor_mod.OK],
                counts[doctor_mod.FAIL],
                counts[doctor_mod.WARN],
                counts[doctor_mod.UNVERIFIED],
            )
        )
        return 1 if failed else 0

    print("sdlc doctor %s" % doctor_mod.VERSION)
    print(
        "raw summary: %d verified, %d FAIL, %d WARN, %d unverified, %d info"
        % (
            counts[doctor_mod.OK],
            counts[doctor_mod.FAIL],
            counts[doctor_mod.WARN],
            counts[doctor_mod.UNVERIFIED],
            counts[doctor_mod.INFO],
        )
    )
    print(
        "action groups: %d blocking, %d needs_human, %d informational"
        % (action_counts["blocking"], action_counts["needs_human"], action_counts["informational"])
    )
    for bucket in ("blocking", "needs_human", "informational"):
        if not groups[bucket]:
            continue
        print("\n[%s]" % bucket)
        for group in groups[bucket]:
            opt_tag = " (optional)" if group["optional"] else ""
            print("- %s%s: %s" % (group["group_id"], opt_tag, group["title"]))
            for finding in group["findings"]:
                print("    %s: %s - %s" % (finding["name"], finding["status"], finding["detail"]))
            print("    next (%s): %s" % (group["command_kind"], group["next_command"]))

    verified_items = [(n, s, d) for n, s, d in results if s == doctor_mod.OK]
    if verified_items:
        print("\n[verified]")
        for name, status, detail in verified_items:
            print("  %s: %s - %s" % (name, status, detail))
    return 1 if failed else 0


def _run_explain(rt_root, parsed):
    # Ensure runtime integrity without touching or creating --root.
    resolve_runtime_file(rt_root, "scripts/doctor.py")
    meta = lookup_check_catalog(parsed.check_id, root_arg=parsed.root)
    if meta is None:
        sys.stderr.write(
            "sdlc explain: unknown check ID %r\n"
            "run 'sdlc doctor --root %s' to inspect active check IDs (examples: codeowners, hook-active, enforcement-readiness).\n"
            % (parsed.check_id, _format_command([parsed.root]))
        )
        return 2

    argv = list(meta["explain_argv"])
    payload = {
        "check_id": meta["check_id"],
        "family": meta["family"],
        "title": meta["title"],
        "optional_in_non_strict": meta["optional_non_strict"],
        "evidence": meta["evidence"],
        "limitation": meta["limitation"],
        "command_kind": meta["command_kind"],
        "next_command_argv": argv,
        "next_command": _format_command(argv),
    }
    if parsed.json:
        print(json.dumps(payload, sort_keys=True))
        return 0

    print("Check: %s (%s)" % (payload["check_id"], payload["family"]))
    print("Summary: %s" % payload["title"])
    print("Evidence: %s" % payload["evidence"])
    print("Limitation: %s" % payload["limitation"])
    print("Next step (%s, not executed): %s" % (payload["command_kind"], payload["next_command"]))
    return 0


SUPPORTED_AGENTS = ("claude", "cursor", "copilot", "codex", "gemini", "opencode", "kilo")


def _parse_agents_csv(raw):
    if raw is None:
        return [], None
    tokens = [part.strip().lower() for part in raw.split(",")]
    if not tokens or any(not tok for tok in tokens):
        return None, "invalid --agents value %r (expected comma-separated list from: %s)" % (
            raw,
            ", ".join(SUPPORTED_AGENTS),
        )
    seen = []
    unknown = []
    for tok in tokens:
        if tok not in SUPPORTED_AGENTS:
            unknown.append(tok)
        elif tok not in seen:
            seen.append(tok)
    if unknown:
        return None, "unsupported --agents selector(s): %s (supported: %s)" % (
            ", ".join(unknown),
            ", ".join(SUPPORTED_AGENTS),
        )
    return seen, None


def _run_lifecycle(rt_root, action, parsed):
    install_mod = load_runtime_module(
        rt_root,
        "_sdlc_delegated_install",
        "scripts/install.py",
        ("scripts/install.py", "scripts/install-manifest.json"),
    )

    if action == "status":
        try:
            report = install_mod.status_project(parsed.root, rt_root)
        except install_mod.InstallError as exc:
            sys.stderr.write("sdlc status: %s\n" % exc)
            return 1
        except OSError as exc:
            sys.stderr.write("sdlc status: %s\n" % exc)
            return 3
        if parsed.json:
            print(json.dumps(report, sort_keys=True))
            return 0
        print("sdlc status: %s" % ("installed (version %s)" % report["state_version"] if report["installed"] else "not installed"))
        print("root: %s" % report["root"])
        print("policy: %s (%s, %s)" % (report["policy"]["path"], report["policy"]["ownership"], report["policy"]["status"]))
        if report["installed_profiles"]:
            print("profiles: %s" % ", ".join(report["installed_profiles"]))
        files = report["files"]
        print(
            "files: %d matching, %d update_available, %d modified, %d missing"
            % (
                len(files["matching"]),
                len(files["update_available"]),
                len(files["modified"]),
                len(files["missing"]),
            )
        )
        for bucket in ("update_available", "modified", "missing"):
            for rel in files[bucket]:
                print("  %s: %s" % (bucket, rel))
        return 0

    if action == "init":
        selected_agents, err = _parse_agents_csv(parsed.agents)
        if err is not None:
            sys.stderr.write("sdlc init: %s\n" % err)
            return 2
        try:
            result = install_mod.init_project(
                parsed.root,
                rt_root,
                agents=selected_agents,
                dry_run=parsed.dry_run,
            )
        except install_mod.InstallError as exc:
            sys.stderr.write("sdlc init: %s\n" % exc)
            if exc.changed:
                sys.stderr.write("partial initialization; changed paths (no completed state published):\n")
                for rel in exc.changed:
                    sys.stderr.write("  %s\n" % rel)
            return 1
        except OSError as exc:
            sys.stderr.write("sdlc init: %s\n" % exc)
            return 3
        if parsed.json:
            print(json.dumps(result, sort_keys=True))
            return 0
        prefix = "dry-run plan" if result["dry_run"] else "initialization complete"
        print("sdlc init (%s): %s" % (prefix, result["setup_mode"]))
        print(
            "policy: %s (%s -> %s)"
            % (result["policy"]["path"], result["policy"]["ownership"], result["policy"]["action"])
        )
        print(
            "owned files: %d planned write(s), %d retained, %d preserved"
            % (
                len(result["planned_writes"]),
                len(result["retained_files"]),
                len(result["preserved_owned_files"]),
            )
        )
        if not result["dry_run"]:
            install_mod.report_controls(result["root"])
        return 0

    if action == "update":
        try:
            result = install_mod.update_project(parsed.root, rt_root, dry_run=parsed.dry_run)
        except install_mod.InstallError as exc:
            sys.stderr.write("sdlc update: %s\n" % exc)
            if exc.changed:
                sys.stderr.write("partial update; changed paths (no completed state published):\n")
                for rel in exc.changed:
                    sys.stderr.write("  %s\n" % rel)
            return 1
        except OSError as exc:
            sys.stderr.write("sdlc update: %s\n" % exc)
            return 3
        if parsed.json:
            print(json.dumps(result, sort_keys=True))
            return 0
        prefix = "dry-run plan" if result["dry_run"] else "update complete"
        print("sdlc update (%s): %s" % (prefix, result["setup_mode"]))
        print(
            "owned files: %d planned write(s), %d retained, %d preserved"
            % (
                len(result["planned_writes"]),
                len(result["retained_files"]),
                len(result["preserved_owned_files"]),
            )
        )
        return 0

    if action == "uninstall":
        try:
            result = install_mod.uninstall_project(parsed.root, rt_root, dry_run=parsed.dry_run)
        except install_mod.InstallError as exc:
            sys.stderr.write("sdlc uninstall: %s\n" % exc)
            if exc.changed:
                sys.stderr.write("partial uninstall; removed paths (ownership state retained for recovery):\n")
                for rel in exc.changed:
                    sys.stderr.write("  %s\n" % rel)
            return 1
        except OSError as exc:
            sys.stderr.write("sdlc uninstall: %s\n" % exc)
            return 3
        if parsed.json:
            print(json.dumps(result, sort_keys=True))
            return 0
        prefix = "dry-run plan" if result["dry_run"] else "uninstall complete"
        print("sdlc uninstall (%s): %d owned file(s) targeted" % (prefix, len(result["planned_removals"])))
        print(
            "policy: %s (%s -> %s)"
            % (result["policy"]["path"], result["policy"]["ownership"], result["policy"]["action"])
        )
        return 0

    sys.stderr.write("sdlc %s: lifecycle operation not yet initialized\n" % action)
    return 3


def main(argv=None):
    return dispatch(argv=argv)


if __name__ == "__main__":
    sys.exit(main())
