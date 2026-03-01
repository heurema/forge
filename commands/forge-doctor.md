---
name: forge doctor
description: Check forge dependencies and configuration
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# /forge-doctor — Health Check

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT}" ]; then echo "Error: CLAUDE_PLUGIN_ROOT not set" >&2; exit 1; fi
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python3 -m forge.cli doctor
```

If forge.local.md is missing, offer to create it:
1. Ask user for paths (skill7 workspace, emporium, website)
2. Write `~/.claude/forge.local.md` with the provided paths

Use the template at `${CLAUDE_PLUGIN_ROOT}/forge.example.md` as reference.
