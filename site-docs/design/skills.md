# Skills

A conceptual take on what agent skills are, why I think the current form is an intermediate one, and how the *workflow* end of the spectrum increasingly belongs to agents rather than skills.

This page is opinion and design rationale, not usage. For the practical reference on the skills that ship inside `abc` (`/record-knowledge`, `/record-skill`, `/contribute-warehouse`), see [Bundled Skills](../concepts/bundled-skills.md).

---

## A Skill Is an Abstraction of a Capability

The best way to view an agent skill is as **an abstraction of a capability** — a modular unit of work the agent knows how to perform. Define a skill by the **outcome it enables**, not by how it is implemented under the hood.

---

## The Spectrum of Skills

Skills exist on a spectrum from purely cognitive to purely mechanical.

### Cognitive skills

A set of instructions, a reasoning framework, or a persona injected into the agent's context. The agent doesn't execute code — it changes *how it thinks*.

**Example:** A "Copywriting Skill" that says: *"Always use the AIDA framework. Here are three examples of good copy..."*

The skill gives the agent a repeatable, reliable way to perform a specific intellectual task.

### Action skills

A deterministic tool the agent can invoke to interact with the outside world — a function call, an API integration, a CLI command.

**Example:** A "Fetch Jira Ticket Skill" that gives the agent an OpenAPI spec to query a Jira instance.

The skill extends the agent's reach beyond its training data into external systems.

### Workflow skills

A multi-step, orchestrated process combining cognitive and action skills — involving loops, conditional logic, multiple prompts, and multiple tools.

**Example:** A "Triage Bug Report Skill" that (1) queries the database for related issues, (2) evaluates severity using a structured prompt, and (3) creates a ticket via API.

---

## Thin Skill, Fat Tools

It's tempting to say *"everything is a prompt"* — that under the hood, even function calls reduce to text instructions the LLM emits and downstream code interprets. That framing is misleading. It collapses an important distinction the current generation of skills actively exploits: **the split between what should be non-deterministic and what should be deterministic.**

A well-designed skill is **thin** — a prompt that orchestrates reasoning, handles the parts that genuinely need a language model (intent classification, decision points, free-form summarisation, what-to-do-next judgement). The prompt is the entry point into a wider set of capabilities.

The capabilities themselves are **fat tools** — CLIs, scripts, library calls — that handle everything deterministic. File I/O. YAML manipulation. Git operations. String formatting that has to come out exactly right every time. You don't want an LLM doing those: it's slow, expensive, and gets details wrong in unpredictable ways. You want a script.

The bundled `contribute-warehouse` skill is the cleanest example in this repo:

| Layer | Concern | Implementation |
|---|---|---|
| **Prompt** | "Are these changes cohesive? Should they be one commit or several? What's a good commit message?" | The agent reasons over the diff in natural language |
| **Tools** | "Stage these specific files. Run the lint gate. Write the commit. Push atomically." | `summarize_changes.py`, `draft_commit_message.py`, `push_warehouse.py`, `abc warehouse contribute` |

The prompt never *writes* a commit. It decides what should be in it; the script executes that decision.

This is what cognitive vs. action skill means in practice:

- A **cognitive skill** is almost entirely prompt — the work *is* the reasoning, and the only "tool" is the LLM's own output. Code review checklists, naming-convention guidance, structured-output templates fit here.
- An **action skill** is a thin prompt that decides *when* and *how* to invoke fat external tools. The skill's value is in the orchestration, not the execution.

Skill authors who don't internalise this end up writing prompts that ask the LLM to do work that should be a script. That produces slow, brittle, expensive skills. The right discipline is the opposite: **push as much as possible into deterministic tools, and let the prompt do only what genuinely requires judgement.**

---

## Why I Think Skills Are an Intermediate Form

Skills, as we package them today — a `SKILL.md` file with frontmatter, optionally bundled with scripts — are a useful response to a current constraint: LLMs need explicit, discoverable instructions to behave consistently across sessions, and we don't yet have a better substrate for distributing those instructions than markdown in a git repo.

I don't think this is the end form of how agents interact with the world. It's an **intermediate state**. A few reasons:

- The packaging is human-curated. Today you author a `SKILL.md`, decide when to invoke it, and maintain it as the model behind it improves. As models get better at long-running planning and at retrieving relevant procedures on demand, the value of *pre-packaging* a repeatable workflow shrinks — the agent can increasingly assemble the procedure itself from looser context.
- Invocation is still largely manual. A user types `/record-skill`. Some coding agents today do attempt auto-invocation — picking up "this looks like a record-skill moment" from context and firing the skill without an explicit slash command — and the results are mixed (sometimes spot-on, often wrong skill / wrong moment). That those attempts exist at all suggests the long-run direction: the slash-command entry point is a holdover from CLI ergonomics, and the discovery layer will eventually move inside the agent itself.
- The artifact / tool / agent boundary is blurry. Right now we say "skills are markdown procedures", "tools are function calls", and "agents are personas that own a workflow". These three categories already overlap. Treating them as three distinct distributable kinds is a packaging decision, not a fundamental one.

Skills as they exist in Agentic Beacon are deliberately the **simplest thing that captures and distributes a repeatable procedure**. That's worth doing today. But I'd expect the shape of "skill" to dissolve as the substrate matures.

---

## Workflow Skills Probably Belong to Agents

Within the spectrum above, the workflow end is where this intermediate-form pressure shows up most clearly.

A pure cognitive skill is just instructions — there's nothing for an agent to own; you load the instructions into context and the LLM follows them. A pure action skill is just a tool — you wrap an API and let the LLM call it.

A workflow skill is different. It implies *state*, *decision points*, *long-running execution across multiple turns*. That looks much more like what an **agent** does than like what a skill does:

- An agent has a name, a persona, a scoped responsibility, and the ability to spawn sub-agents.
- An agent is a more natural home for "this multi-step procedure" than a `SKILL.md` that the parent agent has to remember to follow.
- When the workflow is non-trivial, packaging it as an agent (with its own tools, its own context) gives you isolation and composability that a skill loaded into the parent context doesn't.

In Agentic Beacon, both skills and agents are distributable warehouse artifacts. My current rule of thumb:

| Shape | Better as |
|---|---|
| "Always think this way when reviewing code" | **Skill** (cognitive) |
| "Call this API; here's the contract" | **Skill** (action) |
| "Investigate the failure, decide the fix, write the test, open the PR" | **Agent** |

Where the line falls is a design call, not a mechanical rule. But if you find yourself writing a `SKILL.md` with multiple phases, sub-loops, and "if X then Y else Z" branches, it's a signal you're really describing an agent.

---

## What Skills Are Good At, Today

Setting aside the future, here is the present case for distributing procedures as skills in a warehouse:

- **Cognitive skills** — code review checklists, naming conventions, structured-output templates. These genuinely are "instructions to be followed", they read well as markdown, and they distribute cleanly.
- **Lightly action-flavoured skills** — wrappers around a small, well-defined external tool with a few decision points (the bundled `record-knowledge` skill is roughly this shape — prompt for inputs, write a file at a deterministic path).
- **Low-state procedures** — the steps are linear, the agent doesn't need to remember much between them, and the right behaviour can be expressed in prose.

For everything heavier, prefer an agent. For everything lighter than this, you may not need a skill at all — a paragraph in a context file may do.

---

## See Also

- [Bundled Skills](../concepts/bundled-skills.md) — operational reference for the `record-*` and `contribute-warehouse` skills shipped with `abc`
- [Creating Skills](../guides/creating-skills.md) — how to author and distribute a warehouse skill today
- [Artifact Types](../concepts/artifact-types.md) — skills vs. agents vs. contexts vs. knowledge in the wider artifact matrix
