---
version: 1

defaults:
  codex:
    model: "gpt-5.3-codex"
  gemini:
    model: "gemini-3.1-pro"
  claude:
    model: "sonnet"

routing:
  review:
    codex: "gpt-5.3-codex"
    gemini: "gemini-3-flash"
  implement:
    codex: "gpt-5.3-codex"
    gemini: "gemini-3.1-pro"
  ask:
    codex: "gpt-5.2-codex"
    gemini: "gemini-3-flash"
  default:
    codex: "gpt-5.2-codex"
    gemini: "gemini-3-flash"

fallback:
  order:
    - "codex"
    - "gemini"
  on_error: "skip_warn"
  max_attempts: 2
  timeout_seconds: 120

privacy:
  allow_cross_vendor_fallback: true
---

# Emporium Provider Configuration

Shared model config for arbiter, signum, and other emporium plugins.
Copy to `~/.claude/emporium-providers.local.md` and customize.

## Routing Precedence

1. `routing.<task>.<provider>` — task-specific model
2. `routing.default.<provider>` — default for unknown tasks
3. `defaults.<provider>.model` — provider-level default

## Fallback

When a provider fails, behavior is controlled by `on_error`:
- `skip_warn` — skip provider, warn in stderr, try next in `fallback.order`
- `skip_silent` — skip without warning
- `halt` — stop immediately

## Privacy

`allow_cross_vendor_fallback: true` — allows fallback from one vendor to another.
Set to `false` if code should not be sent to multiple vendors.

## Model Names

Use exact model IDs from provider docs:
- Codex: `gpt-5.3-codex`, `gpt-5.2-codex`, `gpt-5-codex-mini`
- Gemini: `gemini-3.1-pro`, `gemini-3-pro`, `gemini-3-flash`, `gemini-2.5-pro`
- Claude: `opus`, `sonnet`, `haiku`, `claude-opus-4-6`, `claude-sonnet-4-6`
