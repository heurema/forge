---
name: forge audit
description: Quality rubric + cross-repo version consistency check
allowed-tools: Bash, Read, AskUserQuestion
argument-hint: [--plugin NAME] [--allow-stale]
---

# /forge-audit — Quality Audit

Run from inside a plugin directory (or specify plugin name):

```bash
cd $PWD
if [ -z "${CLAUDE_PLUGIN_ROOT}" ]; then echo "Error: CLAUDE_PLUGIN_ROOT not set" >&2; exit 1; fi
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python3 -m forge.cli audit $ARGUMENTS
```

Runs rubric quality checks (12 checks, gate >= 9) and cross-repo consistency (version + description match).

- Default: audits current plugin directory
- `--plugin NAME`: searches workspace for named plugin
- `--allow-stale`: skip rubric freshness check

Present rubric score and any consistency errors.
