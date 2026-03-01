---
name: forge verify
description: Run strict quality checks on current plugin
allowed-tools: Bash, Read
---

# /forge-verify — Quality Gate

Run from inside a plugin directory:

```bash
cd $PWD
if [ -z "${CLAUDE_PLUGIN_ROOT}" ]; then echo "Error: CLAUDE_PLUGIN_ROOT not set" >&2; exit 1; fi
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python3 -m forge.cli verify
```

If checks fail, show all errors and suggest fixes. If checks pass, tell the user they can run `/forge-register`.
