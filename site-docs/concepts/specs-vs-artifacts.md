# Specs vs. Artifacts

Understanding the difference between **specs** and **artifacts** is crucial for effectively using Agentic Beacon. They look similar — both are markdown files an agent reads — but they answer different questions and live in different places.

---

## The Blueprint vs. Building Code Analogy

### Specs = the blueprint ("what" to build)

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
> "I need to build a `POST /users` endpoint that accepts a JSON payload with email and age, and returns a 201 status."

### Artifacts = the building codes & tools ("how" to build it)

Artifacts (managed by the warehouse) are the **reusable heuristics, rules, and capabilities** that govern how the agent writes code to fulfill a spec.

**Examples:**

- Knowledge files (`fastapi-rules.md`, `react-state-management-lessons.md`)
- Skills (`generate-unit-tests`, `code-review`)
- Contexts (`backend-microservice.md`, `python.md`)

**Nature:**

- Organization-wide
- Cross-project and reusable
- Heuristic-driven
- Defines the approach

**Agent's internal monologue:**
> "When I build that `POST /users` endpoint, I must remember to use Pydantic V2 for validation, and I must use the `generate-unit-tests` skill to write a pytest file for it."

---

## How to Handle Them in Your Workflow

Because their purposes are fundamentally different, specs and artifacts live in different places and are handled differently.

### Scenario A: the spec belongs to the local project (most common)

**Rule:** Most of the time, specs should **not** live in your warehouse.

**Example — building a new microservice:**

- The OpenSpec for that microservice lives directly inside the local project repository
- Location: `~/my-project/openspec/spec.md`
- The agent reads the spec directly from the local workspace
- Beacon doesn't sync specs — it only syncs the **knowledge of how to implement** that spec properly

**Workflow:**

```
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
3. Execute `.agentic-beacon/artifacts/skills/` to automate and verify the work

### Scenario B: shared organizational specs (the exception)

**Rule:** Sometimes a spec **is** an organizational artifact and belongs in the warehouse.

**Example — company-wide authentication API:**

- Your company has a core Authentication API
- Every frontend project needs the `auth-openapi.yaml` spec to know how to log users in
- This spec is organizational infrastructure, not project-specific

In this case, store shared specs in the warehouse and reference them in `beacon.yaml`:

```yaml
artifacts:
  contexts:
    - backend/api-design-rules.md     # The "How" — rules for APIs
    - specs/core-auth-api.yaml        # The shared "What" — auth API spec
  skills:
    - generate-api-client             # The "Tool" — generate client code
```

**When to treat specs as artifacts:**

- API contracts shared across multiple teams/projects
- Core platform interfaces that many services integrate with
- Organizational data models or schemas
- Standard communication protocols

---

## The Triangulation

When an agent works in a local project equipped with Beacon, it gets a clean triangulation of data:

| Source | Location | Tells the agent… |
|---|---|---|
| **Local spec** | `./openspec/spec.md` | **What** to code today |
| **Synced knowledge** | `./.agentic-beacon/artifacts/knowledge/` | **How** to follow company standards |
| **Synced skills** | `./.agentic-beacon/artifacts/skills/` | **Procedures** to automate and verify work |

---

## Best Practices

### ✅ Do store in the warehouse (artifacts)

- Coding standards and best practices
- Architectural patterns and guidelines
- Reusable skills and workflows
- Shared organizational contexts
- Common API contracts used across teams

### ❌ Don't store in the warehouse (specs)

- Feature-specific requirements
- Project-specific API endpoints
- Individual user stories
- One-off implementation details
- Project roadmaps and milestones

### 🤔 Gray area (case-by-case)

- **Core platform APIs** — if 10+ projects depend on it → warehouse
- **Data schemas** — if organization-wide standard → warehouse
- **Communication protocols** — if company standard → warehouse

---

## Example: Building a Payment Service

**Local project (specs):**

```
payment-service/
├── openspec/
│   ├── spec.md                    # What: Build payment processing API
│   └── tasks.md                   # What: Stripe integration, refund flow
└── src/
```

**Warehouse (artifacts) referenced by the project's `beacon.yaml`:**

```yaml
artifacts:
  contexts:
    - backend/api-security-rules.md      # How: Handle sensitive data
    - backend/error-handling-patterns.md # How: Return error responses
    - payments/pci-compliance-rules.md   # How: PCI-DSS requirements
    - specs/stripe-api-contract.yaml     # Shared: Stripe integration spec
  skills:
    - generate-api-tests                  # Tool: Generate test suites
    - security-audit                      # Tool: Check for vulnerabilities
```

**Agent's process:**

1. Reads `openspec/spec.md`: "I need to build a payment processing API"
2. Reads `knowledge/api-security-rules.md`: "I must encrypt sensitive data and use HTTPS"
3. Reads `knowledge/pci-compliance-rules.md`: "I must never log credit card numbers"
4. References `specs/stripe-api-contract.yaml`: "Here's how to integrate with the Stripe API"
5. Executes `skills/generate-api-tests`: "Now I'll generate comprehensive test coverage"
6. Executes `skills/security-audit`: "Finally, I'll verify no security vulnerabilities"

---

## Key Takeaway

**Keep Agentic Beacon focused on reusable artifacts** (knowledge, skills, contexts) and **leave feature-specific specs in local project repositories**.

This keeps the warehouse a lean, highly reusable library of agentic intelligence rather than a dumping ground for every project's feature requirements.

---

## See Also

- [How It Works](how-it-works.md) — the warehouse / beacon mental model
- [Artifact Types](artifact-types.md) — the four artifact types and how each is wired
- [beacon.yaml Reference](../reference/beacon-yaml.md) — how to declare artifact dependencies
