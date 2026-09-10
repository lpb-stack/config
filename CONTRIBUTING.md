# Contributing to LocalPibox config

This repo is the **Pi agent configuration preset**: settings, MCP servers,
custom skills, and subagents. It is installed to `~/.pi/agent/` at container
startup.

## What to work on

- **`settings.json.template` / `mcp.json.template` / `lpb-memory-config.json.template`** —
  runtime agent behavior (rendered at first boot → gitignored `settings.json`,
  `mcp.json`, `lpb-memory-config.json`), providers, MCP servers, extension installs.
- **`pi-defaults.json`** — local-first defaults (subagent model, extension overrides).
- **`skills/`** — reusable procedures (each skill is a `SKILL.md`).
- **`agents/`** — subagent definitions. Omit the `model:` field so agents
  inherit the session model; never hardcode a model. `agents/Explore.md`
  overrides the built-in Explore (which pins an Anthropic model) — keep its
  prompt in sync with pi-subagents `src/default-agents.ts` on upgrades.
- **`support/`** — utilities installed to `/opt/pi-support/` (browser
  validation, session UUID, subagent output validation).
- **`install.sh`** — the bootstrap that seeds `~/.pi/agent/`.

## Process

1. Fork the repo, branch off `dev` (the default branch).
2. Make focused, minimal changes and keep `settings.json.template#packages` in
   sync with this README.
3. Open a PR against `dev`.

See the full guide at
[devstack/CONTRIBUTING.md](https://github.com/lpb-stack/devstack/blob/dev/CONTRIBUTING.md).
