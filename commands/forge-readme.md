Generate or update the plugin README from the forge template.

Run from inside a plugin directory:

```bash
PYTHONPATH={{ FORGE_SRC }} python3 -m forge.cli readme
```

Options:
- `--dry-run` — show what would change without writing
- `--force` — overwrite README completely (skip smart merge)
- `--template PATH` — use a custom Jinja2 template instead of built-in
- `--all` — update all plugins in the skill7 workspace

The command uses smart merge by default: it preserves existing section content while adding missing sections, reordering to match the template, and updating the hero/badges/install block.
