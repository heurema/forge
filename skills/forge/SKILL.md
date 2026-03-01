---
name: forge
description: >
  Use when user says "forge new", "create heurema plugin", "scaffold plugin",
  "register plugin in marketplace", "plugin lifecycle", "forge status",
  "forge verify", "forge register", "forge doctor",
  or wants to create, verify, or register a Claude Code plugin for heurema org.
---

# forge — Plugin Lifecycle Manager

Automates the full heurema plugin lifecycle: scaffold, verify, status, register.

## Commands

| Command | When to use |
|---------|-------------|
| `/forge-new <name>` | Creating a brand new plugin from scratch |
| `/forge-status` | Quick health check — what's done, what's missing |
| `/forge-verify` | Before registering — strict quality gate |
| `/forge-register` | Publishing to marketplace + website via PRs |
| `/forge-doctor` | First-time setup or troubleshooting |

## Typical Flow

1. `/forge-doctor` — ensure config and dependencies are set up
2. `/forge-new my-plugin --type marketplace --category devtools` — scaffold
3. Develop the plugin (use plugin-dev skills for content: skills, agents, hooks)
4. `/forge-verify` — check everything is ready
5. `/forge-register` — create PRs for all registries

## Plugin Types

- **marketplace** (default): Full flow — GitHub repo, emporium, website, skill7 registry
- **project**: Git init locally, skill7 registry only
- **local**: Minimal, current directory, no registry

## For Existing Plugins

To register a plugin that already exists but isn't in all registries:
1. `cd` into the plugin directory
2. `/forge-verify` — fix any issues
3. `/forge-register` — creates PRs for missing registries (idempotent)
