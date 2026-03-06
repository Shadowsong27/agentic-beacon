# Example Skill

A template skill showing the structure and format for creating new skills.

**Category:** Example/Template  
**Version:** 1.0.0  
**Last Updated:** 2026-03-06

---

## Purpose

This skill demonstrates the recommended structure for creating reusable agent workflows. Use it as a reference when building domain-specific skills.

---

## When to Use This Skill

Use this skill as a template when you need to:
- Create a new procedural workflow for agents
- Document a multi-step process
- Package templates or scripts with instructions

---

## Prerequisites

- [List any tools, dependencies, or setup required]
- [Example: Git repository initialized]
- [Example: Python 3.10+ installed]

---

## Instructions

### Step 1: [Action Name]

[Detailed instructions for this step]

**Expected outcome:** [What should happen after this step]

**Verification:** [How to check if this step succeeded]

### Step 2: [Action Name]

[Detailed instructions for this step]

**Example:**
```bash
# Command example
example-command --flag value
```

**Expected outcome:** [What should happen]

**Verification:** [How to check success]

### Step 3: [Action Name]

[Continue with all steps in the workflow]

---

## Templates

This skill includes the following templates:

### `templates/example-template.md`
[Describe what this template is for and when to use it]

**Usage:**
1. Copy template to target location
2. Fill in placeholders marked with `[PLACEHOLDER]`
3. Customize sections as needed

---

## Common Issues

### Issue: [Common Problem]
**Symptom:** [How this manifests]  
**Cause:** [Why this happens]  
**Solution:** [How to fix it]

### Issue: [Another Problem]
**Symptom:** [Description]  
**Solution:** [Fix]

---

## Verification

After completing this skill workflow, verify:

- [ ] [Verification criterion 1]
- [ ] [Verification criterion 2]
- [ ] [Verification criterion 3]

**Success criteria:** [What "done" looks like]

---

## Examples

### Example 1: [Scenario Name]

**Context:** [When you would use this]

**Steps:**
1. [Specific steps for this scenario]
2. [Continue...]

**Result:** [What gets produced]

---

## Notes

- [Any additional notes, tips, or warnings]
- [Edge cases to be aware of]
- [Links to related documentation]

---

## Skill Structure Reference

When creating new skills, include:

```
your-skill-name/
├── SKILL.md              # Main instructions (this file)
├── templates/            # Optional: Template files
│   └── template.md
├── scripts/              # Optional: Helper scripts
│   └── helper.sh
├── examples/            # Optional: Example outputs
│   └── example-result.md
└── README.md            # Optional: Additional documentation
```

**Naming conventions:**
- Use kebab-case for directories: `example-skill`, not `example_skill`
- SKILL.md is required and contains agent instructions
- Other components are optional based on needs
