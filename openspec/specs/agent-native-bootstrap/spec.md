# agent-native-bootstrap Specification

## Purpose

Initialize selected coding-agent integrations from shared policy and skill sources while preserving user instructions, safe ownership, and honest discovery claims.

## Requirements

### Requirement: Selected profiles produce native project files
Initialization SHALL support the requested `claude`, `cursor`, `copilot`, `codex`, `gemini`, `opencode`, and `kilo` profiles through documented project-local discovery mechanisms. It SHALL identify each profile's supported surface and command spelling. Unsupported selectors SHALL fail before writes; omitted agent selection SHALL be reported as core-only setup, not agent registration.

#### Scenario: Select an agent profile
- **GIVEN** a supported profile selector and a complete trusted runtime
- **WHEN** initialization is requested for that profile
- **THEN** it produces the profile's documented instruction/skill entries and supported command entries, with the complete core runtime available

#### Scenario: Command mechanisms differ
- **GIVEN** a selected profile with a documented native command surface
- **WHEN** that surface uses manual skills, prompt files, or no custom slash-command file mechanism
- **THEN** the generated integration uses that native mechanism and does not claim a universal `/sdlc:*` spelling or unsupported CLI feature

### Requirement: Canonical project policy is user-owned
Root `AGENTS.md` SHALL be preserved as user-owned policy. Initialization SHALL create a starter only when the file is absent and SHALL not overwrite, adopt as tool-owned, or delete an existing canonical policy. Generated adapters SHALL derive their policy from that source; update and uninstall SHALL retain it.

#### Scenario: Existing instructions
- **GIVEN** a project with a regular, readable root `AGENTS.md`
- **WHEN** initialization plans its policy and adapter outputs
- **THEN** initialization leaves the policy bytes unchanged and uses it as the canonical input

#### Scenario: Fresh policy and later removal
- **GIVEN** initialization created a starter because root `AGENTS.md` was absent
- **WHEN** the toolkit is later uninstalled
- **THEN** the project policy remains and is reported as intentionally retained user content

#### Scenario: Unsafe canonical input
- **GIVEN** a canonical policy that is unreadable, unsafe, or changes during planned publication
- **WHEN** initialization or regeneration validates the policy input
- **THEN** it fails safely rather than replacing the policy or publishing a misleadingly coherent result

### Requirement: Generation has one source and detectable drift
Generated files SHALL derive from shared trusted templates, the canonical skill catalog, and project policy rather than independent hand-maintained copies. Status/update SHALL distinguish stale generated output from user-edited output. Duplicate destinations, overlapping discovery roots, and case collisions SHALL be handled explicitly without overwriting unrelated files or inventing additional product skills.

#### Scenario: Canonical policy changes
- **GIVEN** generated files still match their recorded owned hashes
- **WHEN** the canonical project policy changes
- **THEN** status identifies regeneration needs and update can refresh those generated files without changing the policy

#### Scenario: A generated file was edited
- **GIVEN** a generated file that no longer matches its recorded ownership hash
- **WHEN** regeneration evaluates that destination
- **THEN** it preserves the file and reports the conflict instead of overwriting it

### Requirement: Registration is bounded and non-activating
Initialization SHALL preflight selected outputs and ownership before publishing files. It SHALL not alter global agent configuration, model/permission settings, hooks activation, branch protection, secrets, or hosted settings. Adding a selected profile SHALL not silently remove prior managed profiles or forget their ownership.

#### Scenario: Conflicting pre-existing adapter
- **GIVEN** an intended adapter destination containing differing unowned project content
- **WHEN** initialization preflights the selected profile
- **THEN** it refuses the conflicting plan before publication and reports the affected path

#### Scenario: Add another profile
- **GIVEN** an existing managed installation with one or more selected profiles
- **WHEN** initialization adds another supported profile
- **THEN** prior managed outputs and ownership remain accounted for, with no implicit deselection or deletion

### Requirement: New agent-control files remain protected
Every generated agent-control format SHALL be covered by non-overridable Critical classification at supported repository locations. A broad documentation or Lite rule SHALL not exempt executable instructions, command templates, or skill bodies. Generated text SHALL not evaluate project content through automatic shell-expansion features.

#### Scenario: Attempt to classify a generated command as documentation
- **GIVEN** configuration that labels a generated agent directory Lite or non-executable
- **WHEN** a change modifies a generated agent command or skill
- **THEN** built-in protection still makes the change Critical and prevents a test-evidence exemption

#### Scenario: Project policy contains executable-looking text
- **GIVEN** project policy or arguments containing shell interpolation syntax
- **WHEN** a generated command template renders or loads that data
- **THEN** generation treats the text as data and does not execute it

### Requirement: Discovery evidence states its level
Initialization and documentation SHALL distinguish file generation, native discovery, and observed execution. Fixture/snapshot tests SHALL cover all declared formats, including Claude and Copilot, and actual loader evidence SHALL name its tool version and surface. Unavailable or untested loaders SHALL remain unverified; generating a file SHALL not certify behavior.

#### Scenario: Snapshot passes without a real loader run
- **GIVEN** generated files matching the documented native format
- **WHEN** the target client has not actually loaded them
- **THEN** the result reports configuration/fixture validation only

#### Scenario: Native command or discovery fails
- **GIVEN** an actual loader probe for a generated native entry
- **WHEN** the target cannot discover it or finds an ambiguous duplicate
- **THEN** that profile's acceptance remains incomplete until corrected rather than being counted as supported execution
