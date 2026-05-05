# Specs vs. Artifacts: Understanding the Distinction

## The Blueprint vs. Building Code Analogy

Understanding the difference between **specs** and **artifacts** is crucial for effectively using Agentic Beacon.

### Specs = The Blueprint ("What" to build)

Specs define the **exact, deterministic requirements** of a specific project or feature.

**Examples:**
- OpenSpec files (`openspec.md`)
- OpenAPI definitions (`swagger.yaml`)
- Protobuf definitions (`.proto` files)
- GraphQL schemas
- Product Requirement Documents (PRDs)

**Nature:**
- Project-specific
- Exact and deterministic
- Contract-driven
- Defines the goal

**Agent's internal monologue:**
> "I need to build a POST /users endpoint that accepts a JSON payload with email and age, and returns a 201 status."

### Artifacts = The Building Codes & Tools ("How" to build it)

Artifacts (managed by Agentic Beacon warehouse) are the **reusable heuristics, rules, and capabilities** that govern how the agent writes code to fulfill the spec.

**Examples:**
- Knowledge files (`fastapi-rules.md`, `react-state-management-lessons.md`)
- Skills (`generate-unit-tests`, `code-review`)
- Contexts (`backend-microservice`, `python`)

**Nature:**
- Organization-wide
- Cross-project and reusable
- Heuristic-driven
- Defines the approach

**Agent's internal monologue:**
> "When I build that POST /users endpoint, I must remember to use Pydantic V2 for validation, and I must use the generate-unit-tests skill to write a pytest file for it."

---

## How to Handle Them in Your Workflow

Because their purposes are fundamentally different, specs and artifacts live in different places and are handled differently by the CLI.

### Scenario A: The Spec Belongs to the Local Project (Most Common)

**Rule:** Most of the time, specs should **NOT** live in your central Agentic Beacon warehouse.

**Example:** Building a new microservice
- The OpenSpec for that microservice lives directly inside the local project repository
- Location: `~/my-project/openspec/spec.md`
- The agent reads the spec directly from the local workspace
- Agentic Beacon doesn't sync specs—it only syncs the **knowledge of how to implement** that spec properly

**Workflow:**
```bash
# Project structure
my-project/
├── openspec/
│   └── spec.md                    # Local spec (project-specific)
├── .agentic-beacon/
│   ├── beacon.yaml                # Artifact dependencies (how to build)
│   └── artifacts/
│       ├── knowledge/             # Synced from warehouse
│       └── skills/                # Synced from warehouse
└── src/
```

**Agent's workflow:**
1. Read `openspec/spec.md` to understand **what** to build
2. Read `.agentic-beacon/artifacts/knowledge/` to understand **how** to build it
3. Execute `.agentic-beacon/artifacts/skills/` to automate and verify work

### Scenario B: Shared Organizational Specs (The Exception)

**Rule:** Sometimes a spec **is** an organizational artifact and belongs in the warehouse.

**Example:** Company-wide authentication API
- Your company has a core Authentication API
- Every frontend project needs the `auth-openapi.yaml` spec to know how to log users in
- This spec is organizational infrastructure, not project-specific

**In this case, store shared specs in the warehouse and reference them in beacon.yaml:**

```yaml
# .agentic-beacon/beacon.yaml
artifacts:
    - backend/api-design-rules.md     # The "How" - rules for APIs

  skills:
    - generate-api-client             # The "Tool" - generate client code

  contexts:
    - specs/core-auth-api.yaml        # The shared "What" - auth API spec
```

**When to treat specs as artifacts:**
- API contracts shared across multiple teams/projects
- Core platform interfaces that many services integrate with
- Organizational data models or schemas
- Standard communication protocols

---

## The Ultimate Synergy

When an agent works in a local project equipped with Agentic Beacon, it gets the **perfect triangulation of data**:

### 1. The Goal (Local Spec)
**Location:** `./openspec/spec.md`
**Purpose:** Tells the agent **what** to code today
**Example:** "Build a user registration endpoint with email validation"

### 2. The Rules (Synced Knowledge)
**Location:** `./.agentic-beacon/artifacts/knowledge/`
**Purpose:** Tells the agent **how** to follow company standards
**Example:** "Always use Pydantic V2 for validation, never store passwords in plain text"

### 3. The Engine (Synced Skills)
**Location:** `./.agentic-beacon/artifacts/skills/`
**Purpose:** Automates and verifies the agent's work
**Example:** "Execute test-runner skill to generate and run pytest files"

---

## Best Practices

### ✅ DO Store in Warehouse (Artifacts)
- Coding standards and best practices
- Architectural patterns and guidelines
- Reusable skills and workflows
- Shared organizational contexts
- Common API contracts used across teams

### ❌ DON'T Store in Warehouse (Specs)
- Feature-specific requirements
- Project-specific API endpoints
- Individual user stories
- One-off implementation details
- Project roadmaps and milestones

### 🤔 Gray Area (Case-by-Case)
- **Core platform APIs**: If 10+ projects depend on it → Warehouse
- **Data schemas**: If organization-wide standard → Warehouse
- **Communication protocols**: If company standard → Warehouse

---

## Example: Building a Payment Service

### Local Project (Specs)
```
payment-service/
├── openspec/
│   ├── spec.md                    # What: Build payment processing API
│   └── tasks.md                   # What: Stripe integration, refund flow
└── src/
```

### Warehouse (Artifacts)
```yaml
# .agentic-beacon/beacon.yaml
artifacts:
    - backend/api-security-rules.md      # How: Handle sensitive data
    - backend/error-handling-patterns.md # How: Return error responses
    - payments/pci-compliance-rules.md   # How: PCI-DSS requirements

  skills:
    - generate-api-tests                  # Tool: Generate test suites
    - security-audit                      # Tool: Check for vulnerabilities

  contexts:
    - specs/stripe-api-contract.yaml     # Shared: Stripe integration spec
```

**Agent's Process:**
1. Reads `openspec/spec.md`: "I need to build a payment processing API"
2. Reads `knowledge/api-security-rules.md`: "I must encrypt sensitive data and use HTTPS"
3. Reads `knowledge/pci-compliance-rules.md`: "I must never log credit card numbers"
4. References `specs/stripe-api-contract.yaml`: "Here's how to integrate with Stripe API"
5. Executes `skills/generate-api-tests`: "Now I'll generate comprehensive test coverage"
6. Executes `skills/security-audit`: "Finally, I'll verify no security vulnerabilities"

---

## Key Takeaway

**Keep Agentic Beacon focused on reusable artifacts** (Knowledge, Skills, Contexts) and **leave feature-specific specs in local project repositories**.

This ensures your warehouse remains a **lean, highly reusable library of "Agentic Intelligence"** rather than a dumping ground for every project's random feature requirements.

---

**See Also:**
- [Local Warehouse Workflow](local-warehouse-workflow.md) - How to sync artifacts from warehouse to project
- [Warehouse Structure](../README.md) - Understanding warehouse organization
- [beacon.yaml Reference](../guides/beacon-yaml-reference.md) - How to declare artifact dependencies

**Last Updated:** 2026-03-08
