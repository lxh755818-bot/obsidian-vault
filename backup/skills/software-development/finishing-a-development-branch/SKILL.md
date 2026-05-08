---
name: finishing-a-development-branch
description: Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by presenting structured options for merge, PR, or cleanup
trigger: "完成了|写完了|搞定了|implementation complete|done|finished|all tests pass"
---

# Finishing a Development Branch

## Overview

Guide completion of development work by presenting clear options and handling chosen workflow.

**Core principle:** Verify tests → Present options → Execute choice → Clean up.

## The Process

### Step 1: Verify Tests

Before presenting options, verify tests pass:

```bash
# Run project's test suite (detect project type)
if [ -f "package.json" ]; then npm test
elif [ -f "Cargo.toml" ]; then cargo test
elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then pytest
elif [ -f "go.mod" ]; then go test ./...
else echo "No test framework detected"
fi
```

**If tests fail:**
> "Tests failing (<N> failures). Must fix before completing:
> [show failures]
> Cannot proceed with merge/PR until tests pass."

Stop. Don't proceed to Step 2.

**If tests pass:** Continue to Step 2.

### Step 2: Determine Base Branch

```bash
git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null
```

### Step 3: Present Options

Present exactly these 4 options (no explanation):

```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```

### Step 4: Execute Choice

#### Option 1: Merge Locally

```bash
git checkout <base-branch>
git pull
git merge <feature-branch>
# Verify tests on merged result
npm test / pytest / cargo test
# If tests pass
git branch -d <feature-branch>
```

Then: Cleanup worktree (Step 5)

#### Option 2: Push and Create PR

```bash
git push -u origin <feature-branch>
# Create PR with structured body
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
<2-3 bullets of what changed>

## Test Plan
- [ ] <verification steps>
EOF
)"
```

Then: Cleanup worktree (Step 5)

#### Option 3: Keep As-Is

> "Keeping branch <name>. Worktree preserved at <path>."

**Don't cleanup worktree.**

#### Option 4: Discard

**Confirm first:**
> "This will permanently delete:
> - Branch <name>
> - All commits on this branch
> - Worktree at <path>
>
> Type 'discard' to confirm."

Wait for exact confirmation.

If confirmed:
```bash
git checkout <base-branch>
git branch -D <feature-branch>
```

Then: Cleanup worktree (Step 5)

### Step 5: Cleanup Worktree

**For Options 1, 2, 4:**

```bash
git worktree list | grep $(git branch --show-current)
```

If in worktree:
```bash
git worktree remove <worktree-path>
```

**For Option 3:** Keep worktree.

## Rules

- NEVER skip the test verification step
- NEVER proceed without user choosing an option
- NEVER discard without exact confirmation
- Always cleanup worktrees after merge/PR/discard
