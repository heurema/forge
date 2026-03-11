---
name: forge sync
description: Synchronize plugin.json to all 4 registries
allowed-tools: Bash, Read, AskUserQuestion
argument-hint: [--apply]
---

# /forge-sync — Registry Synchronization

Run from inside a plugin directory:

```bash
cd $PWD
if [ -z "${CLAUDE_PLUGIN_ROOT}" ]; then echo "Error: CLAUDE_PLUGIN_ROOT not set" >&2; exit 1; fi
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python3 -m forge.cli sync $ARGUMENTS
```

Reads plugin.json and writes derived entries to all 4 registries (skill7 registry, emporium marketplace, website marketplace, website plugin-meta).

- Default: dry-run (shows what would change)
- `--apply`: actually write changes

Present the per-target status to the user.
