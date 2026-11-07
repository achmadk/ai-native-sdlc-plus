## Purpose

Defines how the shipped commands and the toolkit's own verification suite behave on native Windows, so platform support is a tested contract rather than an incidental claim.

## ADDED Requirements

### Requirement: Native Windows command entry points

The PowerShell entry points and the red-to-green helper SHALL operate on native Windows without requiring a POSIX shell. Interpreter discovery SHALL evaluate every candidate the platform exposes and select the first candidate that satisfies the supported Python floor, including when one command name resolves to multiple matches and earlier matches are unusable. Command parsing SHALL preserve absolute Windows paths, quoting, and argument boundaries.

#### Scenario: A usable interpreter sits behind an unusable match

- **WHEN** `python` resolves to more than one path candidate and the first candidate cannot run
- **THEN** installation and the advisory hook select a candidate that satisfies the supported Python floor
- **AND** the diagnostic names the candidates that were tried when none qualifies

#### Scenario: Absolute interpreter path contains backslashes

- **WHEN** the red-to-green helper receives a command whose executable is an absolute Windows path
- **THEN** the path reaches the child process intact rather than collapsing into a single token
- **AND** a quoted argument containing spaces remains one argument

#### Scenario: Missing runtime is still reported, not faked

- **WHEN** no candidate satisfies the supported Python floor
- **THEN** the entry point exits nonzero with an actionable message and does not claim a successful install

### Requirement: Platform-portable verification suite

The shipped test suite SHALL execute on native Windows and SHALL report a real verdict rather than an environment artifact. A test that needs a host capability the platform does not provide SHALL skip with a stated reason. Where the underlying behavior can still be asserted without that capability, a portable test SHALL cover it. Test cleanup MUST remove read-only repository objects, reparse points, and temporary trees without turning a passing test into an error.

#### Scenario: A Windows run reaches verdicts

- **WHEN** the suite runs on a supported Windows host where a POSIX shell is available only through the Git installation
- **THEN** shell-dependent tests use that shell
- **AND** the run finishes with passes, reasoned skips, and no environment-caused errors

#### Scenario: Host capability is unavailable

- **WHEN** the host cannot create symlinks or cannot represent a filename that is legal on POSIX
- **THEN** the affected test skips with a reason naming the missing capability
- **AND** the classification behavior behind it is still asserted through an input that does not need the filesystem

#### Scenario: Temporary Git fixtures are removed

- **WHEN** a test removes a temporary Git repository containing read-only objects
- **THEN** cleanup succeeds and the test result reflects only its assertions

#### Scenario: POSIX coverage is not traded away

- **WHEN** a fixture is only executable on POSIX
- **THEN** its assertion remains present for POSIX runs instead of being deleted, weakened, or replaced by a skip everywhere

### Requirement: Windows verification in continuous integration

The repository's CI configuration SHALL execute the Windows contracts on a Windows runner: native installation, filesystem safety, Git-dispatched hook behavior, and the full verification suite. The Windows matrix SHALL include the supported Python floor and a current supported version. Platform-bound skips SHALL appear in job output rather than being silently absent.

#### Scenario: Windows jobs cover install and the full suite

- **WHEN** CI runs for a candidate revision
- **THEN** a Windows job exercises native installation and hook dispatch
- **AND** a Windows job runs the full test suite at the supported Python floor and at a current version

#### Scenario: Compatibility documentation matches the tested matrix

- **WHEN** an operator reads the compatibility documentation
- **THEN** it states the Windows matrix, which suites run there, and which capabilities cause an explicit skip
- **AND** it does not present a configured job as a passing result
