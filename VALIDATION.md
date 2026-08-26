# Config Repo Validation

Validated: 2026-08-07 · Last updated: 2026-08-08 · **Superseded: 2026-08-26**

> ⚠️ **Point-in-time snapshot.** This doc records the repo state at
> 2026-08-07/08. Since then the config repo was re-baselined (`24cf9e0`) —
> the verified table and file layout below no longer match. Current state:
>
> - **`VERSION` removed** — the single stack version source is
>   `devstack/VERSION`; the config repo no longer carries one
> - **`support/` moved to the devstack repo** (Dockerfile COPYs it to
>   `/opt/pi-support/`) — it no longer exists here
> - **`settings.json`** is rendered from `settings.json.template` (gitignored);
>   extension packages are version-pinned via `__LPB_VERSION__`
>   (`lpb-config sync-pins`), not branch refs
> - **`subagents.json` removed** — its settings live in `pi-defaults.json`
> - **`lpb-memory-config.json`** is rendered from
>   `lpb-memory-config.json.template` (gitignored)
>
> The pre-re-baseline findings were resolved in the cleanup commits
> (`9146128`, `9e66e4c`).

## Verified state (as of 2026-08-07)

| Area | Status (then) |
|---|---|
| **README structure** | ✅ Matched actual file layout at the time |
| **settings.json packages** | ⚠️ branch refs `@lpb` / `@main` — now version-pinned |
| **mcp.json** | ✅ runtime file rendered from `mcp.json.template` — exa / agent-browser / context7-mcp enabled, chrome-devtools disabled |
| **skills/** | ✅ 3 skills (agent-browser-mcp-integration, browser-validation, mcp-vision-analysis) |
| **agents/** | ✅ all use `model: parent` (never hardcoded / no Anthropic) |
| **support/** | ⚠️ later moved to the devstack repo |
| **install.sh** | ✅ `echo "Thinking: medium"` matches `defaultThinkingLevel` |
| **VERSION** | ⚠️ `0.2.0-lpb` at the time — later removed from this repo |

## File layout (as of 2026-08-07)

```
config/
├── AGENTS.md
├── VERSION
├── VALIDATION.md
├── README.md
├── install.sh
├── .env.example
├── lpb-memory-config.json
├── settings.json
├── mcp.json.template      # → runtime mcp.json (gitignored)
├── pi-defaults.json
├── subagents.json
├── skills/{agent-browser-mcp-integration,browser-validation,mcp-vision-analysis}/SKILL.md
├── agents/{README,_template,browser-automation,exa-search,researcher}.md
└── support/{browser,browser-state-cleanup.sh,browser-validate.ts,session-uuid.ts,
             validate-subagent-output.ts,config/,docs/,schemas/}
```

Re-run `support/validate-subagent-output.ts` / `browser-validate.ts` as needed
for the browser-validation pipeline (now in the devstack repo).
