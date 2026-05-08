---
name: brainstorming
description: "You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation."
trigger: "create feature|build|add functionality|implement|我要做|我想做|设计一下"
---

# Brainstorming Ideas Into Designs

Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design and get user approval.

<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity.
</HARD-GATE>

## Anti-Pattern: "This Is Too Simple To Need A Design"

Every project goes through this process. A todo list, a single-function utility, a config change — all of them. "Simple" projects are where unexamined assumptions cause the most wasted work. The design can be short (a few sentences for truly simple projects), but you MUST present it and get approval.

## Anti-Pattern: "Just Execute" (When Brainstorming Was Already Done)

If the user has already discussed a plan in conversation, the design phase is complete — do NOT re-brainstorm what's already decided. Applying brainstorming to:
- **Debugging/execution of already-discussed changes** → Skip brainstorming, just execute
- **Bug fixes with clear root cause** → Skip, fix directly
- **Already-approved multi-step plan** → Proceed to implementation without re-designing

Brainstorming's value is in *exploring alternatives before commitment*. Once the user has committed to a direction, re-brainstorming wastes time and can confuse the user ("we already decided this"). Use judgment:
> **If the user described WHAT they want and WHICH approach they prefer → go implement.**
> **If the user said "I want X, I don't know how" → brainstorm first.**

## Checklist

You MUST create a task for each of these items and complete them in order:

1. **Explore project context** — check files, docs, recent commits
2. **Offer visual companion** (if topic will involve visual questions) — this is its own message, not combined with a clarifying question
3. **Ask clarifying questions** — one at a time, understand purpose/constraints/success criteria
4. **Propose 2-3 approaches** — with trade-offs and your recommendation
5. **Present design** — in sections scaled to their complexity, get user approval after each section
6. **Write design doc** — save to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` and commit
7. **Spec self-review** — quick inline check for placeholders, contradictions, ambiguity, scope
8. **User reviews written spec** — ask user to review the spec file before proceeding
9. **Transition to implementation** — invoke writing-plans skill to create implementation plan

## The Process

### Step 1: Explore Project Context

Check files, docs, recent commits to understand current state.

### Step 2: Assess Scope

If the request describes multiple independent subsystems, flag decomposition immediately:
> "This sounds like 3 separate projects. Let's break it down:
> 1. [A] — independent
> 2. [B] — independent  
> 3. [C] — depends on A and B
>
> Which should we start with?"

### Step 3: Ask Clarifying Questions — ONE AT A TIME

Use WHAT/WHY/WHO/WHERE/WHEN framework:
- **WHAT** — What exactly should happen? What does "done" look like?
- **WHY** — Why is this needed now? What happens if we don't?
- **WHO** — Who uses this? Who is affected?
- **WHERE** — What is in/out of scope? What could conflict?
- **WHEN** — Deadlines? Incremental or all-at-once?

Prefer multiple choice when possible.

### Step 4: Propose 2-3 Approaches

Before giving answers, propose alternatives with trade-offs:
> "I can see three approaches:
> **A** — [description] — pros/cons
> **B** — [description] — pros/cons  
> **C** — [description] — pros/cons
>
> My recommendation: **B** because [reason]. Which do you prefer?"

### Step 5: Present Design in Sections

Scale to complexity (few sentences for simple, 200-300 words for nuanced).

Cover: architecture, components, data flow, error handling, testing.

Get approval after each section before moving on.

### Step 6: Write Design Document

Save to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`:
```bash
mkdir -p docs/superpowers/specs
# Write the spec file
git add docs/superpowers/specs/
git commit -m "docs: add [topic] design spec"
```

### Step 7: Spec Self-Review

Quick inline check:
- [ ] Any "TBD", "TODO", or vague requirements?
- [ ] Any sections contradict each other?
- [ ] Is scope focused enough for one plan?
- [ ] Could any requirement be interpreted two ways?

Fix inline. No re-review loop needed.

### Step 8: User Review Gate

> "Spec written and committed. Please review it — let me know if you want any changes before we start the implementation plan."

Wait for approval. If changes requested: make them, re-run self-review, re-submit.

### Step 9: Invoke writing-plans

After user approval, invoke the writing-plans skill to create the implementation plan.

**The ONLY skill you invoke after brainstorming is writing-plans.**

## Key Principles

- **One question at a time** — Don't overwhelm
- **Multiple choice preferred** — Easier to answer
- **YAGNI ruthlessly** — Remove unnecessary features
- **Explore alternatives** — 2-3 approaches before settling
- **Incremental validation** — Get approval before moving on
- **Be flexible** — Go back when something doesn't make sense

## Red Flags

Push back immediately on:
- "Just make it work" → What does "work" mean specifically?
- "Same as X but different" → Exactly how different?
- "Should be simple" → What are the edge cases?
- Vague acceptance criteria → "Improve X" → by how much?
