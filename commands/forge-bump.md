---
name: forge bump
description: Coordinated version bump across plugin.json and all registries
allowed-tools: Bash, Read, AskUserQuestion
argument-hint: <patch|minor|major> [--apply]
---

# /forge-bump — Version Bump

Run from inside a plugin directory:

```bash
cd $PWD
if [ -z "${CLAUDE_PLUGIN_ROOT}" ]; then echo "Error: CLAUDE_PLUGIN_ROOT not set" >&2; exit 1; fi
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python3 -m forge.cli bump $ARGUMENTS
```

Bumps version in plugin.json, updates CHANGELOG.md, and syncs all 4 registries.

- Requires level: `patch`, `minor`, or `major`
- Default: dry-run (shows old → new version)
- `--apply`: actually write changes

Present the version change and per-target sync status.
