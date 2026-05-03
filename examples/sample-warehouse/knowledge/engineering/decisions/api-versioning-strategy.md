# Decision: API Versioning Strategy

**Date:** 2026-01-01
**Status:** Active

---

## Decision

Version APIs via URL path (`/v1/`, `/v2/`) rather than headers or query parameters.

## Implementation

- All public endpoints are prefixed with `/v{n}/`
- Breaking changes require a new version
- Old versions are deprecated with a sunset header before removal

## Consequences

**Positive:**
- Versions are visible in logs and browser URLs
- No special client logic needed to set headers
- Easy to proxy/route by version

**Negative:**
- URLs are longer
- Clients must update base URL on major version
