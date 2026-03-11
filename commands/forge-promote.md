---
name: forge promote
description: Generate promotion checklist for plugin
allowed-tools: Bash, Read, AskUserQuestion
argument-hint: [--output FILE]
---

# /forge-promote — Promotion Checklist

Run from inside a plugin directory:

```bash
cd $PWD
if [ -z "${CLAUDE_PLUGIN_ROOT}" ]; then echo "Error: CLAUDE_PLUGIN_ROOT not set" >&2; exit 1; fi
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python3 -m forge.cli promote $ARGUMENTS
```

Generates a markdown checklist covering: pre-flight checks, awesome list submissions, blog post template, social media templates, and GitHub topic suggestions.

- Default: prints to stdout
- `--output FILE`: writes to file

Present the checklist to the user.
