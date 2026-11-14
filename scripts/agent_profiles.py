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

import importlib.util
import os


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

SUPPORTED_AGENTS = ("claude", "cursor", "copilot", "codex", "gemini", "opencode", "kilo")

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
        if tok not in SUPPORTED_AGENTS:
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
    paths = {
        "CLAUDE.md",
        "GEMINI.md",
        ".github/copilot-instructions.md",
    }
    for prefix in (
        ".claude/skills",
        ".cursor/skills",
        ".github/skills",
        ".agents/skills",
        ".gemini/skills",
        ".opencode/skills",
        ".kilo/skills",
    ):
        for subpath, _, _ in skill_entries:
            paths.add("%s/%s" % (prefix, subpath))
    for spec in COMMAND_OPERATIONS:
        op = spec["op"]
        paths.add(".claude/commands/sdlc/%s.md" % op)
        paths.add(".cursor/skills/sdlc-%s/SKILL.md" % op)
        paths.add(".github/prompts/sdlc-%s.prompt.md" % op)
        paths.add(".gemini/commands/sdlc/%s.toml" % op)
        paths.add(".opencode/commands/sdlc/%s.md" % op)
        paths.add(".kilo/command/sdlc-%s.md" % op)
    return paths


def recover_installed_profiles(owned, source_root):
    """Recover installed profile names in canonical order from validated owned paths."""
    owned_set = set(owned or ())
    markers = {
        "claude": ("CLAUDE.md", ".claude/commands/sdlc/doctor.md", ".claude/skills/ai-sdlc/SKILL.md"),
        "cursor": (".cursor/skills/sdlc-doctor/SKILL.md", ".cursor/skills/ai-sdlc/SKILL.md"),
        "copilot": (
            ".github/copilot-instructions.md",
            ".github/prompts/sdlc-doctor.prompt.md",
            ".github/skills/ai-sdlc/SKILL.md",
        ),
        "codex": (".agents/skills/ai-sdlc/SKILL.md",),
        "gemini": ("GEMINI.md", ".gemini/commands/sdlc/doctor.toml", ".gemini/skills/ai-sdlc/SKILL.md"),
        "opencode": (".opencode/commands/sdlc/doctor.md", ".opencode/skills/ai-sdlc/SKILL.md"),
        "kilo": (".kilo/command/sdlc-doctor.md", ".kilo/skills/ai-sdlc/SKILL.md"),
    }
    recovered = []
    for agent in SUPPORTED_AGENTS:
        if any(m in owned_set for m in markers[agent]):
            recovered.append(agent)
    return recovered


def render_profiles(source_root, selected_agents, policy_text):
    """Render owned file payload entries for the selected agent profiles."""
    agents = parse_agent_selectors(selected_agents)
    if not isinstance(policy_text, str):
        raise install_lib.InstallError("canonical policy text must be a decoded UTF-8 string")
    skill_entries = _read_canonical_skill_sources(source_root)
    items = []
    for agent in agents:
        if agent == "claude":
            items.append(
                _make_item(
                    "CLAUDE.md",
                    _render_policy_adapter(
                        "Claude Code",
                        "Project-local instruction adapter; slash commands use /sdlc:<op> from .claude/commands/sdlc/<op>.md.",
                        policy_text,
                    ),
                )
            )
            items.extend(_render_skill_tree(skill_entries, ".claude/skills"))
            for spec in COMMAND_OPERATIONS:
                items.append(
                    _make_item(
                        ".claude/commands/sdlc/%s.md" % spec["op"],
                        _render_claude_command(spec),
                    )
                )
        elif agent == "cursor":
            items.extend(_render_skill_tree(skill_entries, ".cursor/skills"))
            for spec in COMMAND_OPERATIONS:
                items.append(
                    _make_item(
                        ".cursor/skills/sdlc-%s/SKILL.md" % spec["op"],
                        _render_cursor_command_skill(spec),
                    )
                )
        elif agent == "copilot":
            items.append(
                _make_item(
                    ".github/copilot-instructions.md",
                    _render_policy_adapter(
                        "GitHub Copilot (VS Code surface)",
                        "Repository instructions + .github/skills/*; .github/prompts/sdlc-*.prompt.md are VS Code prompt files only, not a Copilot CLI feature.",
                        policy_text,
                    ),
                )
            )
            items.extend(_render_skill_tree(skill_entries, ".github/skills"))
            for spec in COMMAND_OPERATIONS:
                items.append(
                    _make_item(
                        ".github/prompts/sdlc-%s.prompt.md" % spec["op"],
                        _render_copilot_prompt(spec),
                    )
                )
        elif agent == "codex":
            items.extend(_render_skill_tree(skill_entries, ".agents/skills"))
        elif agent == "gemini":
            items.append(
                _make_item(
                    "GEMINI.md",
                    _render_policy_adapter(
                        "Gemini CLI",
                        "Project-local Gemini CLI instruction adapter (not an Antigravity substitution); commands use /sdlc:<op> from .gemini/commands/sdlc/<op>.toml.",
                        policy_text,
                    ),
                )
            )
            items.extend(_render_skill_tree(skill_entries, ".gemini/skills"))
            for spec in COMMAND_OPERATIONS:
                items.append(
                    _make_item(
                        ".gemini/commands/sdlc/%s.toml" % spec["op"],
                        _render_gemini_command_toml(spec),
                    )
                )
        elif agent == "opencode":
            items.extend(_render_skill_tree(skill_entries, ".opencode/skills"))
            for spec in COMMAND_OPERATIONS:
                items.append(
                    _make_item(
                        ".opencode/commands/sdlc/%s.md" % spec["op"],
                        _render_opencode_command(spec),
                    )
                )
        elif agent == "kilo":
            items.extend(_render_skill_tree(skill_entries, ".kilo/skills"))
            for spec in COMMAND_OPERATIONS:
                items.append(
                    _make_item(
                        ".kilo/command/sdlc-%s.md" % spec["op"],
                        _render_kilo_command(spec),
                    )
                )
    return items
