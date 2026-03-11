# forge

Plugin lifecycle manager for heurema org. Scaffold, verify, register, sync, bump, audit, and promote Claude Code plugins.

## Installation

<!-- INSTALL:START — auto-synced from emporium/INSTALL_REFERENCE.md -->
```bash
claude plugin marketplace add heurema/emporium
claude plugin install forge@emporium
```
<!-- INSTALL:END -->

## Commands

| Command | Description |
|---------|-------------|
| `/forge-new <name>` | Scaffold a new plugin |
| `/forge-status` | Show plugin health dashboard |
| `/forge-verify` | Run strict quality checks |
| `/forge-register` | Register plugin in applicable registries |
| `/forge-readme` | Generate or update README from template |
| `/forge-doctor` | Check dependencies and config |
| `/forge-sync` | Sync plugin.json to all 4 registries |
| `/forge-bump <level>` | Coordinated version bump (patch/minor/major) |
| `/forge-audit` | Quality rubric checks + cross-repo consistency |
| `/forge-promote` | Generate promotion checklist |

## Architecture

`plugin.json` is the Single Source of Truth. All 4 registries (skill7, emporium, website marketplace, website plugin-meta) are derived artifacts kept in sync via `forge sync`.

## Configuration

Requires `~/.claude/forge.local.md` with workspace paths:

```yaml
---
skill7_workspace: ~/personal/skill7
emporium_path: ~/personal/heurema/emporium
website_path: ~/personal/skill7/website
github_org: heurema
---
```

Run `forge doctor` to validate config and dependencies.
