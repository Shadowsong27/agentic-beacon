# Understanding Agent Skills

A conceptual framework for thinking about what agent skills are and how to categorize them.

**Last Updated:** 2026-03-10

---

## What Is an Agent Skill?

The best way to view an agent skill is as an **abstraction of a capability** — a modular unit of work the agent knows how to perform. Define a skill by the **outcome it enables**, not by how it is implemented under the hood.

---

## The Spectrum of Agent Skills

Agent skills exist on a spectrum from purely cognitive to purely mechanical.

### Cognitive Skills

A set of instructions, a reasoning framework, or a persona injected into the agent's context. The agent doesn't execute code — it changes *how it thinks*.

**Example:** A "Copywriting Skill" that says: *"Always use the AIDA framework. Here are three examples of good copy..."*

The skill gives the agent a repeatable, reliable way to perform a specific intellectual task.

### Action Skills

A deterministic tool the agent can invoke to interact with the outside world — a function call, an API integration, a CLI command.

**Example:** A "Fetch Jira Ticket Skill" that gives the agent an OpenAPI spec to query a Jira instance.

The skill extends the agent's reach beyond its training data into external systems.

### Workflow Skills

A multi-step, orchestrated process combining cognitive and action skills — involving loops, conditional logic, multiple prompts, and multiple tools.

**Example:** A "Triage Bug Report Skill" that (1) queries the database for related issues, (2) evaluates severity using a structured prompt, and (3) creates a ticket via API.

---

## The "Everything Is a Prompt" Insight

Under the hood, even function calls are just prompts. When you give an LLM access to a `search_web` tool, you're not giving it code — you're injecting a prompt that says: *"You have access to a tool called search_web. To use it, output JSON formatted like this..."*

The LLM's only interface with the world is text in and text out. The line between a "prompt skill" and a "function skill" is an implementation detail:

- A **cognitive skill** tells the LLM to output natural language formatted in a certain way
- An **action skill** tells the LLM to output JSON formatted in a certain way, which downstream code intercepts and executes

---

## Practical Implications

Think of a skill as a **black-box interface**: it takes an input, does some agentic work, and returns an output. When designing your skill library, don't limit yourself to just one type:

| Skill Type | Example | Implementation |
|---|---|---|
| Cognitive | Code review checklist | `SKILL.md` with structured instructions |
| Action | Fetch GitHub PR diff | `SKILL.md` + tool/API spec |
| Workflow | Full PR review pipeline | `SKILL.md` orchestrating multiple steps and tools |

In Agentic Beacon, `SKILL.md`-based skills are primarily **cognitive and workflow skills** — they package repeatable reasoning processes and multi-step procedures as distributable artifacts. Action skills (tool integrations) are typically handled at the agent tool level rather than in a warehouse.

---

## Further Reading

- [Creating Skills](../guides/creating-skills.md) — How to write and distribute skills in Agentic Beacon
- [Agentic Warehouse Design](./agentic-warehouse-design.md) — Where skills fit in the overall architecture
