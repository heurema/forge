---
name: forge register
description: Register plugin in applicable registries via PRs
allowed-tools: Bash, Read, AskUserQuestion
argument-hint: [--dry-run] [--yes]
---

# /forge-register — Registry Registration

Run from inside a plugin directory:

```bash
cd $PWD
if [ -z "${CLAUDE_PLUGIN_ROOT}" ]; then echo "Error: CLAUDE_PLUGIN_ROOT not set" >&2; exit 1; fi
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python3 -m forge.cli register $ARGUMENTS
```

The CLI handles all registry operations: verify pre-flight, JSON updates, branch creation, commits, and PR creation.

- Default mode: shows diff and asks for confirmation
- `--dry-run`: shows what would be done without making changes
- `--yes`: skips confirmation prompts

Present created PR URLs to the user.
