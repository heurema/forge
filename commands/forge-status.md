---
name: forge status
description: Show plugin health dashboard
allowed-tools: Bash, Read
---

# /forge-status — Plugin Health Dashboard

Run from inside a plugin directory:

```bash
cd $PWD
if [ -z "${CLAUDE_PLUGIN_ROOT}" ]; then echo "Error: CLAUDE_PLUGIN_ROOT not set" >&2; exit 1; fi
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python3 -m forge.cli status
```

Present the output to the user. For any failed checks, suggest the appropriate fix command.
