# Skills

This directory holds reusable workflows available as slash commands in your AI agent.

## Structure

Each skill lives in its own directory with a `SKILL.md` file:

```
skills/
└── my-skill/
    └── SKILL.md    # Instructions the agent follows when the skill is invoked
```

## Adding a Skill

1. Create a directory under `skills/` with a descriptive name
2. Add a `SKILL.md` with the step-by-step instructions for the agent
3. After `abc sync`, the skill becomes available as a slash command in your agent

## Example

```
skills/
└── code-review/
    └── SKILL.md    # "1. Read the diff. 2. Check for X. 3. Report findings..."
```
