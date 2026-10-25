## ADDED Requirements

### Requirement: abc contribute detects when there is nothing to contribute
Before copying files or opening a PR, `abc contribute` SHALL compare local artifacts against the warehouse. If all local artifact files are identical to their warehouse counterparts, the command SHALL print "Nothing to contribute — local artifacts are already in sync with the warehouse." and exit with code 0 without creating a branch or PR.

#### Scenario: All files identical — no-op exit
- **WHEN** `abc contribute` is run AND every local artifact file has identical content to the warehouse file
- **THEN** the CLI prints "Nothing to contribute" and exits with code 0; no git branch is created; no PR is opened

#### Scenario: At least one file differs — proceeds normally
- **WHEN** `abc contribute` is run AND at least one local artifact file differs from the warehouse
- **THEN** the normal contribute flow continues (existing behaviour)

#### Scenario: No artifacts directory — treated as nothing to contribute
- **WHEN** `abc contribute` is run AND `.agentic-beacon/artifacts/` does not exist or is empty
- **THEN** the CLI prints "Nothing to contribute — run 'abc sync' first to download artifacts." and exits with code 0
