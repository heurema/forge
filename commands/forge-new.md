---
name: forge new
description: Scaffold a new heurema plugin with correct repo setup
allowed-tools: Bash, Read, Write, Edit, AskUserQuestion
argument-hint: <plugin-name> [--type marketplace|project|local] [--category devtools|trading|creative]
---

# /forge-new — Create a New Plugin

Run the forge CLI to scaffold a new plugin:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT}" ]; then echo "Error: CLAUDE_PLUGIN_ROOT not set" >&2; exit 1; fi
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python3 -m forge.cli new $ARGUMENTS
```

If the user didn't provide a name, ask for it first.

The CLI handles everything: scaffold, git init, GitHub repo creation (for marketplace), remote setup, and initial push. Present the output and next steps to the user.
