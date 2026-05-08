---
name: qa
description: Test, fix, verify with atomic commits. Improves task completion accuracy and thoroughness.
trigger: /qa
---

# /qa — Quality Assurance Execution Protocol

You are now operating under the **/qa** protocol. Every code change you make MUST follow the test-fix-verify cycle with atomic commits.

## Core Principle

**Nothing ships without proof it works.** Every change is tested before commit, and every commit is self-contained and reversible.

## The TFV Cycle

Every task follows this loop:

### 1. TEST — Understand current state
Before writing any code:
- Run existing tests to establish a baseline: are they passing?
- If fixing a bug: write a failing test that reproduces the bug FIRST
- If adding a feature: write a test that describes the expected behavior FIRST
- Document: "Before my change, the test suite shows ___"

### 2. FIX — Make the minimal change
- Write the minimum code to make the failing test pass
- Do NOT refactor, clean up, or "improve" unrelated code in the same change
- Do NOT add features beyond what was requested
- Each change should do ONE thing

### 3. VERIFY — Prove it works
- Run the full test suite — no regressions
- Run the specific new/modified test — it passes
- Manually verify the behavior if applicable
- Check: "Does this change break anything else?"

### 4. COMMIT — Atomic and descriptive
- Each commit should be one logical change
- Commit message explains WHY, not just WHAT
- If the commit can't be described in one sentence, it's too big — split it

## Test Writing Guidelines

### What to test:
- Happy path: the expected input produces expected output
- Edge cases: empty input, null, boundary values, maximum sizes
- Error cases: invalid input, network failures, permission errors
- Integration: does the component work correctly with its dependencies?

### How to test:
- One assertion per test (or one logical assertion group)
- Test names describe the behavior: `it("returns empty array when no items match filter")`
- Tests should be independent — no shared mutable state between tests
- Tests should be fast — mock external services

### What NOT to test:
- Implementation details (private methods, internal state)
- Framework code (don't test that React renders a div)
- Trivial code (getters, setters, pass-through functions)

## Pre-Commit Checklist

Before every commit, verify:

- [ ] All tests pass (no regressions)
- [ ] New code has test coverage
- [ ] No `console.log` or debug statements left in
- [ ] No commented-out code
- [ ] No TODO comments without a linked issue
- [ ] Linting passes
- [ ] Type checking passes (if applicable)

## Rules

- NEVER commit code without running tests first
- NEVER skip a failing test — fix it or explain why it's wrong
- NEVER combine unrelated changes in one commit
- If tests are slow, still run them — correctness over speed
- If no test framework exists, set one up before writing code
- If you break something, fix it before moving to the next task
