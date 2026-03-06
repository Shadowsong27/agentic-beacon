# Lesson: Session Handoff Patterns

**Agent Failure Mode:** When context becomes too large or token limits are reached, agents often try to continue without properly documenting state, leading to loss of context in the next session.

**Context:** Long-running tasks may span multiple agent sessions due to:
- Token consumption approaching limits
- Natural breaking points in work
- Need to switch contexts or priorities

**Correct Pattern:**

### Before Ending Session

1. **Create checkpoint summary:**
   ```markdown
   ## Session Checkpoint
   
   **What's Complete:**
   - [x] Task 1: Description and verification
   - [x] Task 2: Description and verification
   
   **In Progress:**
   - [ ] Task 3: Current state, what's done, what remains
   
   **Next Steps:**
   - [ ] Task 4: What to do next
   - [ ] Task 5: Subsequent task
   
   **Important Context:**
   - Key decision made: X because Y
   - Files modified: path/to/file1, path/to/file2
   - Dependencies: System/tool that needs to be running
   ```

2. **Document known issues:**
   ```markdown
   **Known Issues to Address:**
   - Issue 1: Description and potential fix
   - Issue 2: Blocked by external factor
   ```

3. **Save checkpoint to project:**
   - In TODO file
   - Or in `.session-handoff.md` file
   - Or as GitHub Issue/PR comment

### Starting New Session

1. **Read checkpoint first** before taking any action
2. **Verify completed items** still work
3. **Resume from documented next steps**
4. **Update checkpoint** as work progresses

**Guardrails:**

Before ending a session, ask:
1. Can someone else (or future me) pick this up without confusion?
2. Have I documented all important decisions made?
3. Are all file paths and dependencies clear?
4. Is the current state verifiable?

**When this matters:**
- Multi-session feature implementations
- Complex debugging that spans days
- Handoffs between different developers/agents
- High token consumption tasks

**Example Good Checkpoint:**
```markdown
## Session Checkpoint - 2026-03-06

**Completed:**
- [x] Created user authentication API endpoint (src/api/auth.py:45-120)
- [x] Added JWT token generation (verified with test_token_generation)
- [x] Database migration for users table (migration 003_add_users)

**In Progress:**
- [ ] Frontend login form - HTML structure done, validation pending
  - File: src/components/LoginForm.tsx
  - Next: Add Yup schema for validation

**Next Steps:**
- [ ] Complete form validation
- [ ] Connect form to API endpoint
- [ ] Add error handling for failed login
- [ ] Write integration tests

**Important Decisions:**
- Using httpOnly cookies (not localStorage) for security
- JWT expiry set to 1 hour (refresh token TBD)

**Environment:**
- Backend running on http://localhost:3000
- Database: PostgreSQL on port 5432
- Auth0 test tenant configured in .env
```

**Anti-pattern (Bad Checkpoint):**
```markdown
Almost done with auth. Need to finish frontend stuff.
```
