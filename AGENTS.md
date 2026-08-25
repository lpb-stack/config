# LocalPibox Pi Agent Configuration

## Architecture

This Pi.dev stack is organized across 6 repositories:

1. **pi** (`lpb-stack/pi`) — Forked and patched Pi monorepo with `reasoning_effort` support for Qwen models
2. **lemonade-pi-plugin** (`lpb-stack/lemonade-pi-plugin`) — Lemonade provider plugin with Qwen reasoning model detection
3. **config** (`lpb-stack/config`) — This repo: settings, skills, agents, support files
4. **devstack** (`lpb-stack/devstack`) — Docker-based development environment
5. **pi-subagents** (`lpb-stack/pi-subagents`) — centralized subagent model registry
6. **lpb-memory** (`lpb-stack/lpb-memory`) — persistent memory extension (subprocess reviews)

## Model Configuration

- **Provider:** lemonade (local LLM server)
- **Model:** Qwen3.6-35B-A3B-MTP-GGUF
- **API endpoint:** `http://127.0.0.1:13305/v1`
- **Thinking level:** medium (default)

The Qwen3.6 model supports thinking (reasoning) via the `enable_thinking` parameter. Pi sends `reasoning_effort` alongside `enable_thinking` to control thinking depth:

| Level | `reasoning_effort` | Description |
|---|---|---|
| `high` | `"high"` | Deep, thorough reasoning |
| `medium` | `"medium"` | Balanced reasoning |
| `low` | `"low"` | Lightweight reasoning |
| `off` | — | No reasoning, direct responses |

Change thinking level with `/settings` in the Pi TUI.

## Qwen3 Thinking Overflow — Known Issue (2026-08-02)

Qwen3.6-35B with thinking enabled throws "context size exceeded" when
`prompt + max_tokens` exceeds the 262k window limit. The following mitigations are in place:

- **maxTokens reduced to ~15k (ratio 0.06)** in the lemonade extension — leaves room for 10-20k thinking blocks
- **`reserveTokens` doubled to 32k** — compaction fires at ~88% (230k) instead of ~94% (246k)
- **Thinking disabled during compaction** — prevents meta-thinking waste on summary generation
- **`LPB_MAX_TOKENS_CONTEXT_RATIO=0.06`** set in `support/start.sh` and `.env.example`
- See `doc/QWEN-THINKING-OVERFLOW.md` and `doc/implementation-plan.md` for full rationale

## MCP Servers

Servers are declared in `mcp.json` (runtime file, rendered from
`mcp.json.template`; the setup wizard's MCP step toggles servers on/off,
`"enabled": false` disables one). The pi-mcp-adapter proxies them — tool
discovery is on-demand, servers start on first use.

### Exa (`exa`)
Web search and content fetch. Requires `EXA_API_KEY` environment variable.

Tools:
- `web_search_exa` — Search the web
- `web_fetch_exa` — Read webpage content

### Agent-Browser (`agent-browser`)
Browser automation for navigation, interaction, screenshots, and visual analysis.

Tools:
- `browser_open`, `browser_click`, `browser_fill`, `browser_type` — Navigation and interaction
- `browser_snapshot`, `browser_screenshot` — Page inspection
- `browser_eval`, `browser_get_text` — DOM access
- Vitual analysis, accessibility audits, performance metrics

### Chrome DevTools (`chrome-devtools`)
Diagnostics only. Disabled by default.

### Context7 (`context7-mcp`)
Pulls up-to-date, version-specific library documentation. Optional `CONTEXT7_API_KEY` for higher rate limits and private repos. Set in environment or `.env`.



## Custom Skills

### agent-browser-mcp-integration
Browser automation workflow. Uses agent-browser MCP for navigation, screenshots, and visual analysis via local Qwen3.6 vision model.

### browser-validation
Automated browser validation pipeline. Navigate, snapshot, screenshot, vitals, accessibility audit, vision analysis, structured JSON report generation.

### mcp-vision-analysis
Analyze webpages visually using the local Qwen3.6-35B vision model.

## Custom Subagents

### researcher (`researcher.md`)
Web research specialist. Searches the web using Exa MCP and synthesizes focused research briefs.

## Support Files

Support utilities are baked into the devstack image. The Dockerfile `COPY`
lines are the source of truth — see `/opt/devstack/` (deployment scripts) and
`/opt/pi-support/` (agent-facing tools). User-facing CLIs are symlinked into
`~/.local/bin` (on PATH):

| Path | Purpose |
|---|---|
| `/opt/devstack/start.sh` | Container start script (config clone, render, entrypoint glue) |
| `/opt/devstack/install-browser.py` | Install Chrome-for-Testing + agent-browser (symlink: `install-browser`) |
| `/opt/devstack/validate.py` | Stack validation helper (symlink: `validate`) |
| `/opt/pi-support/browser-state-cleanup.py` | Cleanup browser state volumes (symlink: `browser-state-cleanup`) |
| `/opt/pi-support/install-openspec.py` | Bootstrap OpenSpec in a project (symlink: `install-openspec`) |
| `/opt/pi-support/browser-validate.ts` | Browser validation entry point |
| `/opt/pi-support/config/agent-browser-action-policy.json` | Agent action policies |
| `/opt/pi-support/config/subagent-browser-prompt.txt` | Subagent browser prompt |
| `/opt/pi-support/docs/subagent-spawning-pattern.md` | Subagent spawning documentation |
| `/opt/pi-support/schemas/browser-validation-schema.json` | Unified JSON validation schema (browser validation + subagent) |
| `/opt/pi-support/session-uuid.ts` | Session UUID generation utility |
| `/opt/pi-support/validate-subagent-output.ts` | Subagent output validation |
| `/opt/pi-support/localpibox/` | Shared Python package for the stack CLIs |
| `/opt/pi-support/lpb-config` | Config repo manager CLI (symlink: `lpb-config`) |
| `/opt/pi-support/lpb-devstack` | DevOps workspace CLI (symlink: `lpb-devstack`) |

## Environment Variables

API keys and configuration are managed across two `.env.example` files:

| File | Convention | Purpose |
|---|---|---|
| `devstack/.env.example` | `LPB_` prefix | Devstack container (used by `lpb.py`) |
| `.pi/agent/.env.example` | bare name | Agent config (used by MCP servers) |

**start.sh bridges `LPB_*` → bare name** for third-party compatibility:

```
LPB_EXA_API_KEY (devstack) → EXA_API_KEY (MCP server reads this)
```

Priority chain (highest → lowest):
1. Shell env (`export EXA_API_KEY=...`)
2. Devstack `.env` file (`LPB_EXA_API_KEY=...`)
3. Runtime defaults (`lpb.conf.env` baked into image)
4. Hardcoded fallback

This means **setting `LPB_EXA_API_KEY` in devstack's `.env` is sufficient** —
`start.sh` automatically promotes it to the bare `EXA_API_KEY` the MCP server needs.

### Bridged Variables

| LPB_ Prefix | Bare Name | Used By |
|---|---|---|
| `LPB_EXA_API_KEY` | `EXA_API_KEY` | Exa MCP server |
| `LPB_CONTEXT7_API_KEY` | `CONTEXT7_API_KEY` | Context7 MCP server |
| `LPB_CONNECTION_TOKEN` | `CONNECTION_TOKEN` | OpenVSCode |
| `LPB_EDITOR_HOST` | `HOST` | OpenVSCode |
| `LPB_ED_PORT` | `ED_PORT` | OpenVSCode |

## Quick Reference

- `/settings` — Change thinking level, theme, delivery, transport
- `/model` — Switch models
- `/session` — Show session info
- `/tree` — Navigate session history
- `/new` — Start new session
- `!command` — Run shell command and send output to model
- `!!command` — Run shell command silently
- `@file` — Include file in message
