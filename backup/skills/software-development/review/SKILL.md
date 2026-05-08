---
name: review
description: Pre-landing PR review with scope drift detection. Sharpens your ability to understand intent before reviewing code.
trigger: /review
---

# /review — Structured Code Review Protocol

You are now operating under the **/review** protocol. When asked to review code changes (PRs, diffs, or patches), you MUST follow this structured review process.

## Core Principle

**Understand the intent, then verify the execution.** A good review catches not just bugs, but scope drift — changes that don't serve the stated goal.

## Review Process

### Phase 1: Understand Intent (before reading code)

1. Read the PR title, description, and linked issues
2. State in one sentence: "The goal of this change is to ___"
3. Identify what should and should NOT change based on this goal

### Phase 2: Scope Check

For every file changed, ask:
- **Is this file change necessary** for the stated goal?
- **Are there unrelated changes** mixed in (formatting, refactoring, feature additions)?
- **Are there missing changes** — files that should have been modified but weren't?

Flag any scope drift:
- "This file was changed but doesn't seem related to the goal"
- "Based on the goal, I'd also expect changes to X but it wasn't modified"

### Phase 3: Correctness Review

For each changed file:

1. **Logic** — Does the code do what the author intended?
2. **Edge cases** — What could break? Null/undefined, empty arrays, concurrent access, boundary values
3. **Error handling** — Are failures handled? Are error messages helpful?
4. **Security** — Any injection risks, exposed secrets, permission issues?
5. **Performance** — Any N+1 queries, unnecessary re-renders, unbounded loops?

### Phase 4: Readability & Maintenance

1. Are variable and function names clear?
2. Is the code self-documenting, or are comments needed?
3. Are new abstractions justified, or are they premature?
4. Will future developers understand this code without the PR context?

### Phase 5: Testing

1. Are there tests for the new/changed behavior?
2. Do existing tests still pass?
3. Are edge cases tested?
4. If no tests: should there be?

## Output Format

```
## Summary
[One sentence: what this PR does]

## Scope
[Is the scope correct? Any drift?]

## Issues
### Must Fix
- [Bugs, security issues, logic errors]

### Should Fix
- [Edge cases, error handling gaps]

### Nits
- [Style, naming, minor improvements]

## Verdict
[APPROVE / REQUEST CHANGES / NEEDS DISCUSSION]
```

## Rules

- NEVER rubber-stamp a review — always provide substantive feedback
- NEVER rewrite the code in the review — point out issues, let the author fix them
- ALWAYS check the diff, not just the final file state — context matters
- Focus on issues that matter, not personal style preferences
- If the PR is too large to review effectively, say so and suggest splitting it
