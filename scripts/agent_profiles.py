"""Deterministic renderer and registry for project-local native agent profiles.

Canonical project policy lives in user-owned root `AGENTS.md`. This module renders
project-local adapter files from trusted sources without modifying global user
settings, model/permission grants, hooks, or shell-evaluating command bodies.
Python >= 3.8; standard library only.
"""

import sys

if sys.version_info < (3, 8):
    sys.exit("agent_profiles requires Python >= 3.8")
sys.dont_write_bytecode = True

import argparse
import hashlib
import importlib.util
import json
import os
import tempfile


def _resolve_install_lib():
    existing = (
        globals().get("install_lib")
        or sys.modules.get("_sdlc_delegated_install")
        or sys.modules.get("scripts.install")
        or sys.modules.get("install")
    )
    if existing is not None and hasattr(existing, "InstallError"):
        return existing
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "install.py")
    spec = importlib.util.spec_from_file_location("_sdlc_delegated_install", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_sdlc_delegated_install"] = mod
    spec.loader.exec_module(mod)
    return mod


install_lib = _resolve_install_lib()

PROFILE_CONTRACT = {
    "claude": {
        "label": "Claude Code",
        "surface": "Claude Code project instructions, skills, and commands",
        "policy_path": "CLAUDE.md",
        "policy_note": "Project-local instruction adapter; slash commands use /sdlc:<op> from .claude/commands/sdlc/<op>.md.",
        "skill_prefix": ".claude/skills",
        "command_path": ".claude/commands/sdlc/{op}.md",
        "command_spelling": "/sdlc:{op}",
        "command_format": "claude-markdown",
    },
    "cursor": {
        "label": "Cursor",
        "surface": "Cursor project skills and manual command skills",
        "policy_path": None,
        "skill_prefix": ".cursor/skills",
        "command_path": ".cursor/skills/sdlc-{op}/SKILL.md",
        "command_spelling": "/sdlc-{op}",
        "command_format": "cursor-manual-skill",
    },
    "copilot": {
        "label": "GitHub Copilot (VS Code surface)",
        "surface": "VS Code Copilot instructions, skills, and prompt files; not Copilot CLI",
        "policy_path": ".github/copilot-instructions.md",
        "policy_note": "Repository instructions + .github/skills/*; .github/prompts/sdlc-*.prompt.md are VS Code prompt files only, not a Copilot CLI feature.",
        "skill_prefix": ".github/skills",
        "command_path": ".github/prompts/sdlc-{op}.prompt.md",
        "command_spelling": "VS Code prompt file: sdlc-{op}",
        "command_format": "copilot-prompt",
    },
    "codex": {
        "label": "Codex",
        "surface": "Codex project instructions and skills; no custom slash commands",
        "policy_path": None,
        "skill_prefix": ".agents/skills",
        "command_path": None,
        "command_spelling": None,
        "command_format": None,
    },
    "gemini": {
        "label": "Gemini CLI",
        "surface": "Gemini CLI project instructions, skills, and TOML commands; not Antigravity",
        "policy_path": "GEMINI.md",
        "policy_note": "Project-local Gemini CLI instruction adapter (not an Antigravity substitution); commands use /sdlc:<op> from .gemini/commands/sdlc/<op>.toml.",
        "skill_prefix": ".gemini/skills",
        "command_path": ".gemini/commands/sdlc/{op}.toml",
        "command_spelling": "/sdlc:{op}",
        "command_format": "gemini-toml",
    },
    "opencode": {
        "label": "OpenCode V2",
        "surface": "OpenCode V2 project instructions, skills, and slash-namespace commands",
        "policy_path": None,
        "skill_prefix": ".opencode/skills",
        "command_path": ".opencode/commands/sdlc/{op}.md",
        "command_spelling": "/sdlc/{op}",
        "command_format": "opencode-markdown",
    },
    "kilo": {
        "label": "Kilo",
        "surface": "Kilo project instructions, skills, and .kilo/command entries; not .kilocode",
        "policy_path": None,
        "skill_prefix": ".kilo/skills",
        "command_path": ".kilo/command/sdlc-{op}.md",
        "command_spelling": "/sdlc-{op}",
        "command_format": "kilo-markdown",
    },
}
SUPPORTED_AGENTS = tuple(PROFILE_CONTRACT)

REPOSITORY_ADAPTERS = (
    (".claude/CLAUDE.md", "claude", "markdown"),
    (".cursorrules", "cursor", "markdown"),
    (".cursor/rules/sdlc.mdc", "cursor", "cursor-rule"),
    (".github/copilot-instructions.md", "copilot", "markdown"),
    ("GEMINI.md", "gemini", "markdown"),
)

PRODUCT_SKILLS = (
    "ai-sdlc",
    "spec-first",
    "context-pack",
    "decision-trace",
    "learning-mode",
    "review-by-intent",
    "verify-and-evals",
    "ship-and-observe",
    "autonomy-policy",
    "ai-readiness-and-metrics",
)

COMMAND_OPERATIONS = (
    {
        "op": "lane",
        "title": "Classify SDLC change risk lane",
        "description": "Classify proposed or changed repository paths into Lite, Standard, or Critical via the SDLC front door.",
        "cli": "python3 scripts/sdlc.py lane --paths <files...>",
    },
    {
        "op": "check",
        "title": "Run SDLC spec, brief, or evidence check",
        "description": "Validate specifications, context briefs, or pull request evidence locally via the SDLC front door.",
        "cli": "python3 scripts/sdlc.py check <spec|brief|evidence> ...",
    },
    {
        "op": "doctor",
        "title": "Inspect SDLC installation and governance health",
        "description": "Run the grouped SDLC doctor check and inspect blocking, needs-human, and informational findings.",
        "cli": "python3 scripts/sdlc.py doctor --root .",
    },
    {
        "op": "status",
        "title": "Inspect SDLC managed ownership and policy status",
        "description": "Read-only inspection of canonical AGENTS.md policy, installed profiles, and managed runtime file state.",
        "cli": "python3 scripts/sdlc.py status --root .",
    },
    {
        "op": "explain",
        "title": "Explain an SDLC doctor check ID and safe next step",
        "description": "Inspect what a doctor check verifies, its limitation, and the exact next command without executing remediation.",
        "cli": "python3 scripts/sdlc.py explain <check-id> --root .",
    },
)


def parse_agent_selectors(selectors):
    """Validate and deduplicate agent profile selectors."""
    if isinstance(selectors, str):
        raw_items = selectors.split(",")
    else:
        raw_items = list(selectors or ())
    if not raw_items:
        raise install_lib.InstallError(
            "empty agent profile selection (supported: %s)" % ", ".join(SUPPORTED_AGENTS)
        )
    seen = []
    unknown = []
    for raw in raw_items:
        if not isinstance(raw, str):
            raise install_lib.InstallError("invalid agent profile selector %r" % (raw,))
        tok = raw.strip().lower()
        if not tok:
            raise install_lib.InstallError(
                "empty agent profile selector in %r (supported: %s)" % (selectors, ", ".join(SUPPORTED_AGENTS))
            )
        if tok not in PROFILE_CONTRACT:
            unknown.append(tok)
        elif tok not in seen:
            seen.append(tok)
    if unknown:
        raise install_lib.InstallError(
            "unsupported agent profile selector(s): %s (supported: %s)"
            % (", ".join(unknown), ", ".join(SUPPORTED_AGENTS))
        )
    return seen


def _make_item(relative, text_or_bytes, mode="0644"):
    install_lib.safe_relative(relative)
    data = text_or_bytes.encode("utf-8") if isinstance(text_or_bytes, str) else bytes(text_or_bytes)
    eff_mode = install_lib.effective_mode(mode)
    return {
        "relative": relative,
        "data": data,
        "record": install_lib.record(data, eff_mode),
    }


def _read_canonical_skill_sources(source_root):
    """Read the allowlisted files for the 10 canonical product skills from install-manifest.json."""
    manifest = install_lib.snapshot(source_root, install_lib.MANIFEST)
    if manifest is None:
        raise install_lib.InstallError("required source missing: %s" % install_lib.MANIFEST)
    parsed = install_lib.load_json(manifest["data"], install_lib.MANIFEST)
    entries = parsed.get("files") or []
    skill_set = set(PRODUCT_SKILLS)
    skill_entries = []
    seen_skill_md = set()
    for entry in entries:
        src = entry.get("source", "")
        parts = src.split("/")
        if len(parts) >= 3 and parts[0] == "skills" and parts[1] in skill_set:
            subpath = "/".join(parts[1:])
            snap = install_lib.snapshot(source_root, src)
            if snap is None:
                raise install_lib.InstallError("required canonical skill source missing: %s" % src)
            if parts[2] == "SKILL.md" and len(parts) == 3:
                seen_skill_md.add(parts[1])
            skill_entries.append((subpath, snap["data"], entry["mode"]))
    missing_skills = sorted(skill_set - seen_skill_md)
    if missing_skills:
        raise install_lib.InstallError(
            "incomplete canonical skill catalog; missing SKILL.md for: %s" % ", ".join(missing_skills)
        )
    return skill_entries


def _render_skill_tree(skill_entries, prefix):
    return [
        _make_item("%s/%s" % (prefix, subpath), data, mode=mode)
        for subpath, data, mode in skill_entries
    ]


def _render_policy_adapter(profile_label, surface_note, policy_text):
    clean_policy = policy_text if policy_text.endswith("\n") else (policy_text + "\n")
    return (
        "<!-- Generated by sdlc from user-owned canonical AGENTS.md for %s. -->\n"
        "<!-- Surface note: %s -->\n"
        "<!-- Edit AGENTS.md and run `sdlc update --root .` to refresh; direct edits here block automatic overwrite. -->\n\n"
        "%s"
    ) % (profile_label, surface_note, clean_policy)


def _render_claude_command(spec):
    return (
        "---\n"
        'description: "%s"\n'
        "disable-model-invocation: true\n"
        "---\n\n"
        "# /sdlc:%s — %s\n\n"
        "Project-local Claude Code command adapter (`/sdlc:%s`).\n"
        "Canonical policy remains in root `AGENTS.md`. Do not evaluate untrusted text as shell commands.\n\n"
        "Run the SDLC front door against the repository root:\n\n"
        "```bash\n"
        "%s\n"
        "```\n"
    ) % (spec["description"], spec["op"], spec["title"], spec["op"], spec["cli"])


def _render_cursor_command_skill(spec):
    return (
        "---\n"
        "name: sdlc-%s\n"
        'description: "%s Manual Cursor command skill (/sdlc-%s)."\n'
        "disable-model-invocation: true\n"
        "---\n\n"
        "# /sdlc-%s — %s\n\n"
        "Manual Cursor command skill (`disable-model-invocation: true`).\n"
        "Canonical project policy lives in root `AGENTS.md` (do not create deprecated `.cursor/commands/` files).\n\n"
        "Run the SDLC front door against the repository root:\n\n"
        "```bash\n"
        "%s\n"
        "```\n"
    ) % (spec["op"], spec["description"], spec["op"], spec["op"], spec["title"], spec["cli"])


def _render_copilot_prompt(spec):
    return (
        "---\n"
        'description: "%s"\n'
        "---\n\n"
        "# sdlc-%s — %s (VS Code prompt-file surface)\n\n"
        "Surface boundary: `.github/prompts/sdlc-%s.prompt.md` is a VS Code GitHub Copilot Chat prompt-file surface only; "
        "it is not a Copilot CLI or cloud-agent slash-command feature.\n\n"
        "Run the SDLC front door from the repository root:\n\n"
        "```bash\n"
        "%s\n"
        "```\n"
    ) % (spec["description"], spec["op"], spec["title"], spec["op"], spec["cli"])


def _escape_toml_basic_string(value):
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )


def _render_gemini_command_toml(spec):
    desc = _escape_toml_basic_string(spec["description"])
    prompt_body = (
        "# /sdlc:%s — %s\n\n"
        "Native Gemini CLI custom command (`/sdlc:%s`; not an Antigravity substitution).\n"
        "Canonical project policy lives in root `AGENTS.md` (with `GEMINI.md` generated as a read-only adapter).\n"
        "Do not embed shell command execution blocks in this TOML template.\n\n"
        "Run the SDLC front door against the repository root:\n\n"
        "```bash\n"
        "%s\n"
        "```\n"
    ) % (spec["op"], spec["title"], spec["op"], spec["cli"])
    return (
        "# Generated by sdlc for Gemini CLI (/sdlc:%s).\n"
        'description = "%s"\n'
        'prompt = "%s"\n'
    ) % (spec["op"], desc, _escape_toml_basic_string(prompt_body))


def _render_opencode_command(spec):
    return (
        "---\n"
        'description: "%s"\n'
        "---\n\n"
        "# /sdlc/%s — %s\n\n"
        "Native OpenCode V2 command file (`/sdlc/%s` slash namespace; OpenCode V2 reads root `AGENTS.md` and does not use `CLAUDE.md` as an instruction fallback).\n"
        "Do not use shell interpolation syntax in this command file.\n\n"
        "Run the SDLC front door against the repository root:\n\n"
        "```bash\n"
        "%s\n"
        "```\n"
    ) % (spec["description"], spec["op"], spec["title"], spec["op"], spec["cli"])


def _render_kilo_command(spec):
    return (
        "---\n"
        'description: "%s"\n'
        "---\n\n"
        "# /sdlc-%s — %s\n\n"
        "Native Kilo command file (`.kilo/command/sdlc-%s.md` -> `/sdlc-%s`; never create legacy `.kilocode/`).\n"
        "Canonical project policy remains in root `AGENTS.md`.\n\n"
        "Run the SDLC front door against the repository root:\n\n"
        "```bash\n"
        "%s\n"
        "```\n"
    ) % (spec["description"], spec["op"], spec["title"], spec["op"], spec["op"], spec["cli"])


def recognized_profile_paths(source_root):
    """Return the exact set of relative paths that supported agent profiles can manage."""
    skill_entries = _read_canonical_skill_sources(source_root)
    paths = set()
    for descriptor in PROFILE_CONTRACT.values():
        if descriptor["policy_path"]:
            paths.add(descriptor["policy_path"])
        prefix = descriptor["skill_prefix"]
        for subpath, _, _ in skill_entries:
            paths.add("%s/%s" % (prefix, subpath))
        if descriptor["command_path"]:
            for spec in COMMAND_OPERATIONS:
                paths.add(descriptor["command_path"].format(op=spec["op"]))
    return paths


def recover_installed_profiles(owned, source_root):
    """Recover installed profile names in canonical order from validated owned paths."""
    owned_set = set(owned or ())
    recovered = []
    for agent, descriptor in PROFILE_CONTRACT.items():
        markers = {descriptor["skill_prefix"] + "/ai-sdlc/SKILL.md"}
        if descriptor["policy_path"]:
            markers.add(descriptor["policy_path"])
        if descriptor["command_path"]:
            markers.add(descriptor["command_path"].format(op="doctor"))
        if owned_set & markers:
            recovered.append(agent)
    return recovered


def render_profiles(source_root, selected_agents, policy_text):
    """Render owned file payload entries for the selected agent profiles."""
    agents = parse_agent_selectors(selected_agents)
    if not isinstance(policy_text, str):
        raise install_lib.InstallError("canonical policy text must be a decoded UTF-8 string")
    skill_entries = _read_canonical_skill_sources(source_root)
    command_renderers = {
        "claude-markdown": _render_claude_command,
        "cursor-manual-skill": _render_cursor_command_skill,
        "copilot-prompt": _render_copilot_prompt,
        "gemini-toml": _render_gemini_command_toml,
        "opencode-markdown": _render_opencode_command,
        "kilo-markdown": _render_kilo_command,
    }
    items = []
    for agent in agents:
        descriptor = PROFILE_CONTRACT[agent]
        if descriptor["policy_path"]:
            items.append(_make_item(
                descriptor["policy_path"],
                _render_policy_adapter(descriptor["label"], descriptor["policy_note"], policy_text),
            ))
        items.extend(_render_skill_tree(skill_entries, descriptor["skill_prefix"]))
        if descriptor["command_path"]:
            command_renderer = command_renderers[descriptor["command_format"]]
            for spec in COMMAND_OPERATIONS:
                items.append(_make_item(descriptor["command_path"].format(op=spec["op"]),
                                        command_renderer(spec)))
    return items


def render_repository_adapters(policy_text):
    """Render named compatibility files without adopting or writing them."""
    if not isinstance(policy_text, str):
        raise install_lib.InstallError("canonical policy text must be a decoded UTF-8 string")
    policy = policy_text if policy_text.endswith("\n") else policy_text + "\n"
    items = []
    for path, agent, wrapper in REPOSITORY_ADAPTERS:
        prefix = ""
        if wrapper == "cursor-rule":
            prefix = (
                "---\n"
                "description: AI-native SDLC lane routing and evidence rules\n"
                'globs: ["*"]\n'
                "alwaysApply: true\n"
                "---\n\n"
            )
        header = (
            "<!-- Generated %s repository compatibility policy from AGENTS.md.\n"
            "Not installer-owned; edit canonical policy and regenerate this output. -->\n\n"
        ) % PROFILE_CONTRACT[agent]["label"]
        items.append(_make_item(path, prefix + header + policy))
    return items


def _repository_adapter_plan(root):
    root = os.path.abspath(root)
    policy = install_lib.inspect_canonical_policy(root)
    if policy["status"] != "present":
        raise install_lib.InstallError("required canonical policy missing: AGENTS.md")
    report = {"matching": [], "missing": [], "modified": []}
    items = render_repository_adapters(policy["text"])
    current_records = {}
    for item in items:
        actual = install_lib.snapshot(root, item["relative"])
        item["previous"] = actual
        current_records[item["relative"]] = actual["record"] if actual is not None else None
        if actual is None:
            report["missing"].append(item["relative"])
        elif actual["data"] == item["data"]:
            report["matching"].append(item["relative"])
        else:
            report["modified"].append(item["relative"])
    install_lib.unchanged(root, "AGENTS.md", policy["snapshot"])
    report = {key: sorted(values) for key, values in report.items()}
    report["policy_sha256"] = policy["snapshot"]["record"]["sha256"]
    report["adapters_sha256"] = hashlib.sha256(
        json.dumps(current_records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return policy, items, report


def repository_adapter_status(root):
    """Inspect compatibility drift without changing policy or adapter files."""
    return _repository_adapter_plan(root)[2]


def generate_repository_adapters(root, policy_sha256, adapters_sha256):
    """Publish only the five named adapters after exact snapshot approval."""
    for approved_hash in (policy_sha256, adapters_sha256):
        if not isinstance(approved_hash, str) or not install_lib.HASH.fullmatch(approved_hash):
            raise install_lib.InstallError("explicit policy and adapter approval hashes are required")
    root = os.path.abspath(root)
    policy, items, report = _repository_adapter_plan(root)
    if policy_sha256 != report["policy_sha256"] or adapters_sha256 != report["adapters_sha256"]:
        raise install_lib.InstallError("canonical policy or adapters changed since approval; review the new plan")
    pending = [item for item in items
               if item["previous"] is None or item["previous"]["record"] != item["record"]]
    staged = []
    changed = []
    try:
        install_lib.unchanged(root, "AGENTS.md", policy["snapshot"])
        for item in items:
            install_lib.unchanged(root, item["relative"], item["previous"])
        for item in pending:
            destination = install_lib.checked_path(root, item["relative"])
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            destination = install_lib.checked_path(root, item["relative"])
            descriptor, temporary = tempfile.mkstemp(prefix=".sdlc-adapter-", dir=os.path.dirname(destination))
            item["staged"] = temporary
            staged.append(temporary)
            install_lib.write_staged(descriptor, temporary, item)
            install_lib.verify_staged(temporary, item)
        for item in pending:
            destination = install_lib.checked_path(root, item["relative"])
            install_lib.verify_staged(item["staged"], item)
            install_lib.unchanged(root, "AGENTS.md", policy["snapshot"])
            install_lib.unchanged(root, item["relative"], item["previous"])
            os.replace(item["staged"], destination)
            changed.append(item["relative"])
        install_lib.verify_payload(root, items)
        install_lib.unchanged(root, "AGENTS.md", policy["snapshot"])
        result = repository_adapter_status(root)
        result["changed"] = sorted(changed)
        return result
    except (OSError, ValueError, install_lib.InstallError) as exc:
        raise install_lib.InstallError("repository adoption failed: %s" % exc, changed) from exc
    finally:
        for temporary in staged:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def run(argv=None):
    parser = argparse.ArgumentParser(description="Inspect or explicitly adopt repository compatibility adapters")
    subcommands = parser.add_subparsers(dest="command")
    repository = subcommands.add_parser("repository", help="check or regenerate the five named repository adapters")
    repository.add_argument("--root", default=".")
    mode = repository.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report drift without writing")
    mode.add_argument("--adopt", action="store_true", help="publish the exact approved policy and adapter snapshots")
    repository.add_argument("--policy-sha256")
    repository.add_argument("--adapters-sha256")
    repository.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command != "repository":
        parser.print_help()
        return 2
    if args.adopt and (not args.policy_sha256 or not args.adapters_sha256):
        parser.error("--adopt requires --policy-sha256 and --adapters-sha256 from the reviewed --check report")
    if args.check and (args.policy_sha256 or args.adapters_sha256):
        parser.error("approval hashes apply only to --adopt")
    try:
        if args.adopt:
            result = generate_repository_adapters(args.root, args.policy_sha256, args.adapters_sha256)
        else:
            result = repository_adapter_status(args.root)
    except (OSError, install_lib.InstallError) as exc:
        if args.json:
            print(json.dumps({"error": str(exc), "changed": list(getattr(exc, "changed", ()))}, sort_keys=True))
        else:
            sys.stderr.write("repository adapters: %s\n" % exc)
        return 1
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("repository adapters: %d matching, %d missing, %d modified" % (
            len(result["matching"]), len(result["missing"]), len(result["modified"])))
    return 1 if result["missing"] or result["modified"] else 0


if __name__ == "__main__":
    sys.exit(run())
