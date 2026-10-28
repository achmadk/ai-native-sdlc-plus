# Optional tools

Three standalone helpers that sit next to the core gate. They are stdlib-only
Python, they do not change the behaviour of `lane.py`, `evidence_check.py` or
`doctor.py`, and nothing runs them automatically. Each addresses an item in
[`LIMITATIONS.md`](../LIMITATIONS.md).

> `install.sh` / `install.ps1` may copy a fixed list of scripts. If these
> tools are missing after an install, copy `scripts/trace_lint.py`,
> `scripts/lane_backtest.py` and `scripts/doctor_online.py` manually or add
> them to the installer.

## `scripts/trace_lint.py` - is the evidence more than paperwork?

`evidence_check.py` verifies that evidence *exists*. `trace_lint.py` asks a few
cheap follow-ups. It is heuristic and never judges whether content is good.

| Code | Level | Meaning |
|---|---|---|
| `placeholder` | error | unedited template text (`TODO`, `TBD`, `<describe ...>`, `{{var}}`, `Label: ...`) |
| `empty-section` | warning | a heading with nothing under it |
| `empty-field` | warning | a `Label:` line with no value |
| `bad-link` | error | a relative link whose target does not exist, or escapes the repo root |
| `no-spec-link` | error | only with `--require-spec-link`: the body has no usable link |
| `no-tests` | error | Standard/Critical lane changes source files but no test files |
| `no-independent-reviewer` | warning | only with `--author`: no reviewer other than the author |

```
python3 scripts/trace_lint.py --body-file pr_body.md \
    --git-diff origin/main --lane Standard --author alice --reviewer bob

gh pr view 12 --json body -q .body | python3 scripts/trace_lint.py --body-file -
```

HTML comments are ignored (they are template instructions). Use
`--ignore-line REGEX` for legitimate matches such as "removed TODO comments",
`--strict` to treat warnings as errors and `--advisory` to always exit 0.

Known limits: link checking only covers relative links and treats any
`http(s)` link as present without fetching it; the test-file check is
path-based and knows common naming conventions only.

## `scripts/lane_backtest.py` - calibrate lanes on your own history

```
python3 scripts/lane_backtest.py --limit 50
python3 scripts/lane_backtest.py --rev origin/main --limit 200 --json
```

Replays `lane.py` over the last N first-parent commits (one merge or squash
commit is one change) and prints the lane distribution plus the most frequent
matched rules. If nearly everything lands in Critical, or nothing does, adjust
`lane-config` before rolling the gate out.

It calls `lane.py --paths <files...>`. If your `lane.py` expects another
shape use `--paths-style comma` or `--paths-style repeat`. Output it cannot
parse is reported as `unclassified`, and commits touching more than
`--max-files` files are skipped rather than truncated.

## `scripts/doctor_online.py` - is the gate actually required?

```
python3 scripts/doctor_online.py --check gate
python3 scripts/doctor_online.py --check gate --repo owner/name --branch main
```

Uses the GitHub CLI (`gh`, authenticated with read access to branch
protection) to confirm that the named status check is required by classic
branch protection or a ruleset, and warns when `enforce_admins` is off.
`--check` must match the context name shown in GitHub's settings, which is
normally the job name rather than the workflow name.

Exit codes: `0` required, `1` not required, `2` could not verify.

It cannot see ruleset bypass actors; review those in Settings. A repository
owner can still change any of this, as `LIMITATIONS.md` says: the goal is to
make an accidental gap visible, not to make bypass impossible.

## Tests

```
python3 -m unittest discover -s tests -p "test_extras_*.py" -v
```

The `extras-tests` workflow runs the same command when `scripts/` or `tests/`
change.
