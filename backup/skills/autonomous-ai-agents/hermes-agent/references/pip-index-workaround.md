# pip Index Workaround — Session Reference

**Date:** 2026-05-05
**Trigger:** `hermes update` on Termux/Android with tsinghua PyPI mirror configured

## Symptom

`hermes update` timed out (120s) with this chain:

```
ConnectionAbortedError: [Errno 103] Software caused connection abort
  → pip._vendor.urllib3.exceptions.ProtocolError: ("Connection broken: ConnectionAbortedError(103, ...)")
  → pip install wheel build of .whl files fails
```

This is NOT a network dropout — it is the China mirror rejecting `.whl` binary wheels with HTTP 403, then pip retries over the same mirror and eventually times out.

## Root Cause

System pip.conf or pip.ini is configured to use `https://pypi.tuna.tsinghua.edu.cn/simple` (tsinghua mirror). This mirror works for pure-Python sdist files but frequently 403s on platform-specific `.whl` binary wheels. hermes-agent's `pyproject.toml` declares build dependencies (setuptools, wheel) that pip tries to build from sdist, but the build process itself may also need binary wheels, causing the same failure.

## Fix Applied

```bash
cd /data/data/com.termux/files/home/hermes-agent
venv/bin/python -m pip install setuptools --index-url https://pypi.org/simple/ -q
venv/bin/pip install -e . --index-url https://pypi.org/simple/
```

Two-step: (1) upgrade setuptools first with explicit index to ensure the build backend is current, (2) then `pip install -e .` with explicit index.

## Verification

```bash
cd /data/data/com.termux/files/home/hermes-agent
venv/bin/pip show hermes-agent | grep Version
# → Version: 0.12.0

cat ~/.hermes/gateway_state.json
# → "gateway_state": "running"
```

## Gateway Restart Command

```bash
rm -f ~/.hermes/gateway.pid
hermes gateway run --replace &
sleep 18
cat ~/.hermes/gateway_state.json
```
