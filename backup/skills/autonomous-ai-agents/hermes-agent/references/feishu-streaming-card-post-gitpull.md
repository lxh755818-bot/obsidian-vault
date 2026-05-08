# hermes-feishu-streaming-card: Post-git-pull Patch Re-apply

**Date:** 2026-05-07
**Trigger:** `hermes update` on Termux/Android with `hermes-feishu-streaming-card` installed

---

## Symptom

After `git pull` succeeds, running the card plugin's installer:

```bash
cd ~/.hermes/plugins/hermes-feishu-streaming-card
/hermes/venv/bin/python -m hermes_feishu_card.cli setup --hermes-dir /path/to/hermes-agent --yes
```

Fails with:

```
error: install state incomplete; manifest missing
```

Or, if restore is attempted:

```
error: run.py changed since install; refusing to restore
```

## Root Cause

`hermes-feishu-streaming-card` installs by:
1. Backing up the original `run.py` and recording its SHA256 in `~/.hermes/plugins/hermes-feishu-streaming-card/.install_manifest.json`
2. Patching `run.py` with AST-based hook injection (markers: `HERMES_FEISHU_CARD_PATCH_BEGIN`, etc.)
3. Starting a sidecar process

When `git pull` fetches upstream changes to `run.py`, it **overwrites** the patched file, making the manifest SHA mismatch. The `setup` CLI validates the manifest before doing anything — if SHA doesn't match (or manifest is missing), it refuses to run. `restore` also refuses because `run.py` no longer matches the backed-up original.

## Why `git stash` Before `git pull` Also Causes This

If local modifications to `run.py` were stashed before `git pull` (as happened here — the old patch was stashed), the stash stores the **old patched** version. After `git pull` Fast-forwards to the latest upstream, the stash still holds a patched version, but the working tree has the clean new upstream. The `setup` CLI sees `run.py` as "clean upstream" with no patch, so it rejects with "manifest missing".

## Correct Fix: Apply Patch Directly

Do NOT use the `setup` CLI or `restore`. Call the patcher's `apply_patch()` function directly on the current (now clean upstream) `run.py`:

```bash
cd ~/.hermes/plugins/hermes-feishu-streaming-card
/hermes/venv/bin/python -c "
import sys
sys.path.insert(0, 'hermes_feishu_card/install')
from patcher import apply_patch

run_py = '/data/data/com.termux/files/home/hermes-agent/gateway/run.py'
patched = apply_patch(open(run_py).read())
open(run_py, 'w').write(patched)
print('Patch applied successfully')
"
```

Where:
- `sys.path.insert(0, 'hermes_feishu_card/install')` — adds the installer's patcher module to the Python path
- `apply_patch()` — the AST-based patcher from the plugin; handles idempotent re-application (checks for existing markers and skips if already present)
- The `venv` must be Hermes's own venv (has `aiohttp`), not the system Python

## After Patching: Restart Everything

```bash
# Restart gateway
rm -f ~/.hermes/gateway.pid
hermes gateway run --replace &
sleep 15

# Restart sidecar
python -m hermes_feishu_card.cli start
```

## Verify

```bash
# Check gateway
cat ~/.hermes/gateway_state.json
# → feishu: connected

# Check patch is present
grep "HERMES_FEISHU_CARD" /data/data/com.termux/files/home/hermes-agent/gateway/run.py
# → multiple matches including PATCH_BEGIN, PATCH_END, TOOL_PATCH, ANSWER_DELTA_PATCH, THINKING_DELTA_PATCH, COMPLETE_PATCH

# Check sidecar log
tail -3 ~/.hermes_feishu_card/sidecar.log
```

## Key Files

| File | Purpose |
|------|---------|
| `~/.hermes/plugins/hermes-feishu-streaming-card/hermes_feishu_card/install/patcher.py` | AST-based patch injector |
| `~/.hermes/plugins/hermes-feishu-streaming-card/hermes_feishu_card/install/detect.py` | Hermes version/structure validator |
| `~/.hermes/plugins/hermes-feishu-streaming-card/.install_manifest.json` | SHA manifest (becomes invalid after git pull) |
| `~/.hermes/plugins/hermes-feishu-streaming-card/hermes_feishu_card/hook_runtime.py` | Runtime emit functions called by patched hooks |

## Patcher Patch Blocks

The patcher injects 6 blocks into `gateway/run.py`:

1. **`HERMES_FEISHU_CARD_PATCH_BEGIN/END`** — inside `_handle_message_with_agent` docstring, calls `emit_from_hermes_locals(locals())`
2. **`HERMES_FEISHU_CARD_COMPLETE_PATCH_BEGIN/END`** — near the `return response` of the handler, calls `emit_from_hermes_locals_async(...)` with `answer`, `duration`, `model`, `tokens`, `context`
3. **`HERMES_FEISHU_CARD_TOOL_PATCH_BEGIN/END`** — inside `_run_agent`, calls `emit_from_hermes_locals_threadsafe(...)` for `tool.updated` events
4. **`HERMES_FEISHU_CARD_ANSWER_DELTA_PATCH_BEGIN/END`** — inside `_run_agent`, for streaming `answer.delta` events
5. **`HERMES_FEISHU_CARD_THINKING_DELTA_PATCH_BEGIN/END`** — inside `_run_agent`, for `thinking.delta` events

Each block is idempotent — `apply_patch()` checks that the existing block matches expected content and skips if already correct.
