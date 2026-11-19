
<!-- SDLC Governance Plan Additions -->
## SDLC Risk Lane & Artifact Obligations

- **Lane Classification**: Determine risk lane before coding (`Lite`, `Standard`, or `Critical`) by running `sdlc lane --paths <files...>`.
- **Standard Lane**: Normal feature development. No threat-note or rollout-plan required; deliberate skips of Critical artifacts are permitted without generating fake notes.
- **Critical Lane**: Security, authentication, data migrations, or payment logic. Requires dedicated `threat-note.md` and `rollout-plan.md` in the feature folder before gate acceptance.

