# LocalPibox Pi Agent Config

Reproducible Pi.dev agent configuration: settings, MCP servers, custom skills, subagents, and bootstrap install script.

> **⚡ [← Back to LocalPibox](https://github.com/lpb-stack)** — project overview, architecture, and the full stack.

## Repository Structure

```
config/
├── AGENTS.md              # Global agent instructions
├── lpb-memory-config.json # Memory extension config
├── install.sh             # One-command bootstrap script
├── .env.example           # Environment variables template
├── mcp.json.template      # MCP server template (rendered at first boot → mcp.json)
├── skills/                # Custom skills (installed to ~/.pi/agent/skills/)
│   ├── agent-browser-mcp-integration/
│   │   └── SKILL.md
│   ├── browser-validation/
│   │   └── SKILL.md
│   └── mcp-vision-analysis/
│       └── SKILL.md
├── agents/                # Custom subagents (installed to ~/.pi/agent/agents/)
│   ├── README.md
│   ├── _template.md
│   ├── browser-automation.md
│   ├── exa-search.md
│   └── researcher.md
└── support/               # Shared utilities (installed to /opt/pi-support/)
    ├── browser            # Source script for browser environment
    ├── browser-state-cleanup.sh
    ├── browser-validate.ts
    ├── session-uuid.ts
    ├── validate-subagent-output.ts
    ├── config/
    │   ├── agent-browser-action-policy.json
    │   └── subagent-browser-prompt.txt
    ├── docs/
    │   └── subagent-spawning-pattern.md
    └── schemas/
        ├── browser-validation-schema.json
        └── subagent-browser-schema.json
```



```
# Install with defaults (to ~/.pi/agent/)
bash install.sh

# Install to custom location
bash install.sh /path/to/custom/pi/agent
```

## lpb-config Utility

Shipped in the devstack image at `/opt/pi-support/lpb-config` (symlinked to
`lpb-config` in PATH). Manage the config repo from inside any container.

### Commands

```
lpb-config status               # Show config repo state
lpb-config update               # Fetch + fast-forward config repo
lpb-config reset [--force]      # Re-clone (destructive)
lpb-config merge                # Interactive merge
lpb-config render [--force]     # Regenerate runtime config from templates
lpb-config align                # Update extension pins to latest tags
lpb-config sync-pins            # Sync extension pins to the pipeline's stack version
lpb-config setup                # First-run setup wizard (provider, model, memory)
lpb-config check                # Validate the installation (read-only checklist)

lpb-config memory show          # Show lpb-memory config
lpb-config memory setup         # Interactive config wizard
lpb-config memory setup --non-interactive  # Generate from template
```

`sync-pins` is pipeline-sensitive: `lpb-config --tag main sync-pins` syncs
pins to the stable stack version. Workspace/validate operations live in
`lpb-devstack` (dev-time tool):

```
lpb-devstack validate                          # Full stack alignment check
lpb-devstack workspace status | sync           # Workspace repo management
```

### Template rendering

This repo ships templates (`settings.json.template`,
`lpb-memory-config.json.template`, `mcp.json.template`); the rendered runtime
files are gitignored.
`start.sh` generates them on first boot only, so lpb-config also renders:
`reset` re-renders (force), `update`/`merge` re-render (non-forcing), and
`lpb-config render [--force]` regenerates on demand. Non-forcing render never
overwrites — it creates missing files and warns on stale version pins;
`--force` merges (user keys and user-added packages preserved; template pins
win in `settings.json`, local keys win in the memory config).

## Configuration

### settings.json
- **Provider:** lemonade (external LLM server)
- **Model / endpoint:** runtime config — `lpb-config show` (change with
  `lpb-config set model|base-url|api-key` or the `lpb setup` wizard)
- **Thinking:** medium (default); adjustable via `/settings` in Pi TUI or
  `lpb-config set thinking`
- **Packages:** extensions installed at runtime (from `settings.json#packages`):
  - `git:github.com/lpb-stack/lemonade-pi-plugin@lpb`
  - `git:github.com/lpb-stack/lpb-memory@main`
  - `npm:pi-mcp-adapter`
  - `git:github.com/lpb-stack/pi-subagents@lpb`
  - `npm:pi-powerline-footer`

### lpb-memory-config.json

Configuration for the lpb-memory extension. Generated at first boot from
`lpb-memory-config.json.template` — the template is tracked, the config is not.

```bash
# Review current config
lpb-config memory show

# Interactive setup wizard
lpb-config memory setup

# Non-interactive (from template)
lpb-config memory setup --non-interactive
```

Default settings (from template):
- **reviewTransport**: subprocess (offload to NPU)
- **memoryMode**: legacy-inject (visible to AI every turn)
- **memoryCharLimit**: 3000 (context optimized)
- **failureInjectionMaxEntries**: 3
- **No llmModelOverride** — uses main model (user configures after /login)

### mcp.json
MCP server configuration — **runtime file**, rendered from `mcp.json.template`
at first boot (gitignored; the setup wizard's MCP step, step 6, offers an
enable/disable toggle per server — `"enabled": false` turns a server off):
- **exa** — Web search and content fetch (requires EXA_API_KEY)
- **agent-browser** — Browser automation
- **chrome-devtools** — Diagnostics (disabled by default)
- **context7-mcp** — Up-to-date library docs (optional CONTEXT7_API_KEY)

## Environment Variables

Copy `.env.example` to `.env` in your project directory and fill in:
- `EXA_API_KEY` — Exa MCP server API key
- `CONNECTION_TOKEN` — OpenVSCode auth token
- `EDITOR_HOST` — Editor host for VSCodium
- `ED_PORT` — Editor port

## LocalPibox Stack

This repo is the **configuration preset** for the LocalPibox stack. On first
container boot, these files are seeded into `~/.pi/agent/`.

| Repo | Role |
|---|---|
| [devstack](https://github.com/lpb-stack/devstack) | Container image + `lpb` launcher |
| [pi](https://github.com/lpb-stack/pi) | Pi monorepo fork (Qwen reasoning) |
| [lemonade-pi-plugin](https://github.com/lpb-stack/lemonade-pi-plugin) | Lemonade provider extension |
| [pi-subagents](https://github.com/lpb-stack/pi-subagents) | Subagent model registry |
| [lpb-memory](https://github.com/lpb-stack/lpb-memory) | Persistent memory extension |
| [config](https://github.com/lpb-stack/config) | This repo (settings, skills, agents) |

See the [devstack](https://github.com/lpb-stack/devstack) repo for container setup
and [localpibox.github.io](https://localpibox.github.io) for the project site.

## Contributing

See the [stack CONTRIBUTING guide](https://github.com/lpb-stack/devstack/blob/main/CONTRIBUTING.md).
