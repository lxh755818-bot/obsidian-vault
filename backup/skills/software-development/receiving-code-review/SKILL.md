---
name: receiving-code-review
description: Use when receiving code review feedback, before implementing suggestions - requires technical rigor and verification, not performative agreement or blind implementation
trigger: "review feedback|code review|有人 review|收到反馈"
---

# Receiving Code Review Feedback

## Overview

Code review requires technical evaluation, not emotional performance.

**Core principle:** Verify before implementing. Ask before assuming. Technical correctness over social comfort.

## The Response Pattern

```
WHEN receiving code review feedback:

1. READ: Complete feedback without reacting
2. UNDERSTAND: Restate requirement in own words (or ask)
3. VERIFY: Check against codebase reality
4. EVALUATE: Technically sound for THIS codebase?
5. RESPOND: Technical acknowledgment or reasoned pushback
6. IMPLEMENT: One item at a time, test each
```

## Forbidden Responses

**NEVER:**
- "You're absolutely right!" (performative)
- "Great point! / Excellent feedback!" (performative)
- "Let me implement that now" (before verification)

**INSTEAD:**
- Restate the technical requirement
- Ask clarifying questions
- Push back with technical reasoning if wrong
- Just start working (actions > words)

## Handling Unclear Feedback

```
IF any item is unclear:
  STOP — do not implement anything yet
  ASK for clarification on unclear items

WHY: Items may be related. Partial understanding = wrong implementation.
```

**Example:**
```
Reviewer says: "Fix 1-6"
You understand: 1, 2, 3, 6. Unclear on: 4, 5.

WRONG: Implement 1,2,3,6 now, ask about 4,5 later
RIGHT: "I understand items 1,2,3,6. Need clarification on 4 and 5 before proceeding."
```

## Source-Specific Handling

### From Human Partner
- **Trusted** — implement after understanding
- **Still ask** if scope unclear
- **No performative agreement**
- **Skip to action** or technical acknowledgment

### From External Reviewers

BEFORE implementing:
1. Check: Technically correct for THIS codebase?
2. Check: Breaks existing functionality?
3. Check: Reason for current implementation?
4. Check: Works on all platforms/versions?
5. Check: Does reviewer understand full context?

**IF suggestion seems wrong:**
Push back with technical reasoning.

**IF can't easily verify:**
> "I can't verify this without [X]. Should I [investigate/ask/proceed]?"

## One Item At A Time

Implement and test each feedback item individually before moving to the next:
1. Fix item 1 → test → verify
2. Fix item 2 → test → verify
3. ...

This prevents cascading failures from combined changes.

## Remember

- Technical rigor over social comfort
- Verify against codebase reality, not assumptions
- Ask before implementing unclear feedback
- Push back with reasoning if suggestions are wrong
- Test each fix individually
