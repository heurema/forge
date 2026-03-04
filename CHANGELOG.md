# Changelog

## 0.3.0

- Add skill activation logging hook (PostToolUse → Skill matcher)
- Logs skill_id, loaded, session_id, timestamp to ~/.local/share/emporium/activation.jsonl
- Self-kill watchdog (2s timeout), single jq call, atomic printf writes

## 0.2.0

- Add `forge readme` command — generate/update README from template
- Add `--all` mode — batch update all plugins in workspace
- Smart merge — preserves existing section content while adding missing sections
- User-configurable templates via `readme_template` in forge.local.md
- Enhanced `forge verify` — validates README structure and style
- Updated built-in README.md.j2 template with badges, sections, privacy

## 0.1.0

- Initial scaffold
