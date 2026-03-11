# Changelog

## 0.3.0

- Add `forge sync` — sync plugin.json to all 4 registries (dry-run default)
- Add `forge bump` — coordinated version bump across plugin.json + registries
- Add `forge audit` — rubric quality checks + cross-repo consistency
- Add `forge promote` — promotion checklist generator
- Add rubric snapshot vendoring (populated by `forge doctor`)
- Rewrite `forge register` to use sync internally + preflight + resume
- Add `forge doctor` rubric refresh + gh auth check
- Fix forge.local.md website_path
- plugin.json is now SSoT — all registries are derived artifacts

## 0.2.0

- Add `forge readme` command — generate/update README from template
- Add `--all` mode — batch update all plugins in workspace
- Smart merge — preserves existing section content while adding missing sections
- User-configurable templates via `readme_template` in forge.local.md
- Enhanced `forge verify` — validates README structure and style
- Updated built-in README.md.j2 template with badges, sections, privacy

## 0.1.0

- Initial scaffold
