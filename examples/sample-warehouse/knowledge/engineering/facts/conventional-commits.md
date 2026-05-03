# Fact: Conventional Commits Format

**Last Updated:** 2026-01-01

---

## Overview

Conventional Commits is a specification for structured commit messages that enables automated changelogs and semantic versioning.

## Details

**Format:** `<type>(<scope>): <description>`

**Common types:**
- `feat` — new feature (triggers minor version bump)
- `fix` — bug fix (triggers patch version bump)
- `refactor` — code change without behavior change
- `docs` — documentation only
- `test` — test changes
- `chore` — build/config changes

**Breaking changes:** append `!` → `feat!: rename endpoint`

## Usage/Application

Tools like Release-Please and semantic-release parse these to auto-generate changelogs and bump versions without manual intervention.

## Important Notes

- The scope is optional but recommended for large repos
- Breaking changes can also be declared in the commit footer: `BREAKING CHANGE: <description>`
