---
name: skill-authoring
description: Create new Hermes Agent skills with proper structure and progressive disclosure. Use when user asks to create, write, or build a new skill, or when existing skills lack proper name/description frontmatter for correct skill router loading.
---

# Skill Authoring

## When to Create a Skill

Create a skill when:
- A complex, multi-step workflow is used repeatedly
- A non-trivial approach was discovered through trial and error
- User explicitly asks to "remember how to do X"
- An existing workflow lacks proper skill routing metadata

## Skill Directory

Skills live in: `~/.hermes/skills/`

## SKILL.md Required Structure

```md
---
name: skill-name
description: Brief description of what this skill does. Use when [specific trigger conditions - file types, keywords, contexts that cause this skill to load].
---

# Skill Name

## Quick Start
[Minimal working example - shortest path to first success]

## Workflows
[Step-by-step processes with checklists for complex tasks]

## Advanced Features
[Link to separate files: See [REFERENCE.md](REFERENCE.md)]
```

## Description Rules (CRITICAL)

The `description` field is the **only thing the skill router sees** when deciding whether to load a skill. Bad descriptions = skill never triggers.

**Format:**
- Max 1024 chars
- Third person
- First sentence: what it does
- Second sentence: "Use when [specific triggers]"

**Good:**
```
Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when user mentions PDFs, forms, or document extraction.
```

**Bad:**
```
Helps with documents.
```

**Triggers must be specific**, not generic:
- Good: `Use when user asks about A2A task claiming or EvoMap API`
- Bad: `Use when working with APIs`

## File Splitting Rules

| Condition | Action |
|-----------|--------|
| SKILL.md exceeds 100 lines | Split into SKILL.md + REFERENCE.md |
| Content has distinct domains | Split by domain |
| Advanced features rarely needed | Move to separate file |
| Deterministic operations repeated the same way | Add scripts/ helper |

## Scripts

Add utility scripts when:
- Operation is deterministic (validation, formatting, error detection)
- Same code would be generated repeatedly
- Errors need explicit, reproducible handling

Scripts save tokens and improve reliability vs generated code.

## Process

1. **Gather requirements** — ask user about: domain, specific use cases, whether scripts needed, reference materials
2. **Draft the skill** — create SKILL.md (required) + reference files if needed
3. **Review with user** — present draft and verify coverage

## Review Checklist

- [ ] Description includes triggers ("Use when...")
- [ ] SKILL.md under 100 lines
- [ ] No time-sensitive info in description
- [ ] Consistent terminology
- [ ] Concrete examples included
- [ ] References one level deep (no deep nesting of See ALSO)

## Example: API Error Handling Pattern

When building skills that call external APIs, document response shapes explicitly:

```python
# API returns {"error": "task_full"} NOT {"status": "..."}
# Must handle both shapes:
CLAIM_STATUS=$(echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
err = d.get('error', '')
if err:
    print('error_' + err)
else:
    print(d.get('status', 'unknown'))
")
```
