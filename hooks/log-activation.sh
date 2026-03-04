#!/bin/bash
# PostToolUse hook: log Skill tool activations to JSONL
# Receives JSON on stdin: {tool_name, tool_input, tool_output}
# Non-blocking: enforces timeout=2 seconds via self-kill mechanism

timeout=2

INPUT="$(cat)"

# Session ID from env var, fallback to date+PID
SESSION_ID="${CLAUDE_SESSION_ID:-$(date +%Y%m%d_%H%M%S)_$$}"

_main() {
    local tool_name
    tool_name="$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)" || true

    if [ "$tool_name" != "Skill" ]; then
        exit 0
    fi

    # Single jq call: extract all fields at once
    local parsed
    parsed="$(echo "$INPUT" | jq -r '[
        (.tool_input.skill // .tool_input.id // .tool_input.skill_id // .tool_input.name // "unknown"),
        (if (.tool_output // "") != "" then "true" else "false" end)
    ] | @tsv' 2>/dev/null)" || parsed="unknown	false"

    local skill_id="${parsed%%	*}"
    local loaded="${parsed##*	}"

    local timestamp
    timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    local entry
    entry="$(jq -cn \
        --arg skill_id "$skill_id" \
        --arg timestamp "$timestamp" \
        --arg session_id "$SESSION_ID" \
        --argjson loaded "$loaded" \
        --argjson followed "null" \
        --arg plugin_name "forge" \
        '{skill_id: $skill_id, timestamp: $timestamp, session_id: $session_id, loaded: $loaded, followed: $followed, plugin_name: $plugin_name}'
    )"

    # Log location: XDG Base Directory spec
    local log_dir="${XDG_DATA_HOME:-$HOME/.local/share}/emporium"
    mkdir -p "$log_dir"
    printf '%s\n' "$entry" >> "$log_dir/activation.jsonl"
}

# Start self-kill watchdog: SIGKILL after $timeout seconds
( sleep $timeout && kill -9 $$ 2>/dev/null ) &
WATCHDOG=$!

_main 2>/dev/null

# Cancel watchdog if finished in time
kill $WATCHDOG 2>/dev/null || true
wait $WATCHDOG 2>/dev/null || true

exit 0
