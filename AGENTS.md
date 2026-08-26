# LocalPibox Pi Agent Configuration

## Runtime settings — read them, don't guess

Model, Lemonade endpoint, thinking level, MCP servers, and memory settings
are **runtime config, not fixed facts** — never assume a model name or
endpoint. Source of truth:

```
lpb-config show          # all effective runtime settings (compact)
lpb-config show --json   # machine-readable
lpb-config models        # models served by the configured Lemonade server
```

Amend (non-interactive, validated live): `lpb-config set model|thinking|base-url|api-key`.
Interactive: `lpb-config setup` (wizard) or in-Pi `/model` / `/settings`.
The Lemonade server is an **external host** persisted in `~/.pi/agent/auth.json`
(`lpb-config show` prints it); `LEMONADE_*` env vars are startup defaults.

## How this context is composed

- **This file** — stable stack facts only (architecture, workflows, CLI map).
  Kept deliberately small; it is injected at every session start.
- **lpb-memory** — dynamic learnings from past sessions (failures,
  preferences, insights), injected at startup under character limits and
  managed via `lpb-config memory`. Don't store static facts here.
- **Runtime values** — live in rendered config (settings.json, auth.json,
  mcp.json, lpb-memory-config.json); inspect with `lpb-config show`.

## Architecture

This Pi.dev stack is organized across 6 repositories (all under
`github.com/lpb-stack`):

1. **pi** (`lpb-stack/pi`) — forked Pi monorepo with `reasoning_effort` support for Qwen models
2. **lemonade-pi-plugin** — Lemonade provider plugin (Qwen thinking handling)
3. **config** (`lpb-stack/config`) — this repo: settings, skills, agents, support files
4. **devstack** (`lpb-stack/devstack`) — Docker-based development environment (single source of VERSION)
5. **pi-subagents** — centralized subagent model registry
6. **lpb-memory** — persistent memory extension (subprocess reviews)

## Thinking (reasoning)

The Lemonade model serves thinking via `enable_thinking`; Pi sends
`reasoning_effort` alongside it. Levels: `off`, `minimal`, `low`, `medium`
(default), `high`, `xhigh`, `max`. Change with `/settings` or
`lpb-config set thinking <level>`.

Known issue: Qwen models with thinking enabled throw "context size exceeded"
when `prompt + max_tokens` exceeds the window. Mitigations baked into the
stack: `max_tokens` capped at ~6% of the context window
(`LPB_MAX_TOKENS_CONTEXT_RATIO=0.06`), `reserveTokens` raised so compaction
fires earlier, thinking disabled during compaction.

## MCP Servers

Declared in `mcp.json` (rendered from `mcp.json.template`; the setup wizard's
MCP step toggles servers, `"enabled": false` disables one). pi-mcp-adapter
proxies them — tool discovery is on-demand, servers start on first use.
Live state: `lpb-config show`.

- **exa** — web search + content fetch (`EXA_API_KEY`)
- **agent-browser** — browser automation: navigation, interaction,
  screenshots, vision analysis
- **chrome-devtools** — diagnostics only, disabled by default
- **context7-mcp** — version-specific library docs (optional
  `CONTEXT7_API_KEY` for higher limits)

## Custom Skills

- **agent-browser-mcp-integration** — browser automation workflow (navigation,
  screenshots, visual analysis via the configured vision model)
- **browser-validation** — navigate, snapshot, screenshot, vitals,
  accessibility audit, vision analysis, structured JSON report
- **mcp-vision-analysis** — visual page analysis via the Lemonade vision API

## Custom Subagents

- **researcher** — web research via Exa MCP; focused research briefs

## Support CLIs

Baked into the devstack image (`/opt/devstack/`, `/opt/pi-support/`);
symlinked into `~/.local/bin` (on PATH):

| CLI | Purpose |
|---|---|
| `lpb-config` | Config repo manager + runtime settings (`show`/`set`/`setup`/`render`/`memory …`) |
| `lpb-devstack` | DevOps workspace (`bump`, `workspace sync/status`, `validate`, `release …`) |
| `install-browser` | Install Chrome-for-Testing + agent-browser (with system deps) |
| `validate` | Stack validation helper |
| `install-openspec` | Bootstrap OpenSpec in a project |
| `browser-state-cleanup` | Cleanup browser state volumes |

## Environment Variables

Two `.env.example` files: `devstack/.env.example` (`LPB_` prefix, used by
`lpb.py`) and `.pi/agent/.env.example` (bare names, used by MCP servers).
`start.sh` bridges `LPB_*` → bare name, so setting e.g.
`LPB_EXA_API_KEY` in devstack's `.env` is sufficient. Priority (high → low):
shell env → devstack `.env` → `lpb.conf.env` (baked) → fallback.

Bridged: `LPB_EXA_API_KEY`→`EXA_API_KEY` (exa), `LPB_CONTEXT7_API_KEY`→`CONTEXT7_API_KEY`
(context7), `LPB_CONNECTION_TOKEN`→`CONNECTION_TOKEN`, `LPB_EDITOR_HOST`→`HOST`,
`LPB_ED_PORT`→`ED_PORT` (OpenVSCode).

## Quick Reference

- `/settings` — thinking level, theme, delivery, transport · `/model` — switch models
- `/session`, `/tree`, `/new` — session info / history navigation / new session
- `!cmd` — run shell, send output to model · `!!cmd` — run silently · `@file` — include file
- `lpb-config show` — what model/server/thinking is actually active right now
