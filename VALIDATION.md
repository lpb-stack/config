# Config Repo Validation

Validated: 2026-08-07 · Last updated: 2026-08-08

## Status: ✅ Current & consistent

The prior validation findings were resolved in the cleanup commits
(`9146128`, `9e66e4c`). This doc has been refreshed to record the current
verified state.

## Verified state

| Area | Status |
|---|---|
| **README structure** | ✅ Matches actual file layout (flat `support/`, all agent files listed, `lpb-memory-config.json` documented) |
| **settings.json packages** | ✅ README matches `settings.json` (5 extensions; branch refs `@lpb` / `@main`) |
| **mcp.json** | ✅ runtime file rendered from `mcp.json.template` — exa / agent-browser / context7-mcp enabled, chrome-devtools disabled |
| **skills/** | ✅ 3 skills (agent-browser-mcp-integration, browser-validation, mcp-vision-analysis) |
| **agents/** | ✅ 5 files; all use `model: parent` (never hardcoded / no Anthropic) |
| **support/** | ✅ Match `/opt/pi-support` layout (config/, docs/, schemas/) |
| **install.sh** | ✅ `echo "Thinking: medium"` matches `defaultThinkingLevel` |
| **lpb-memory-config.json** | ✅ Documented in README, installed by install.sh, copied by devstack |
| **VERSION** | ✅ `0.2.0-lpb` (source of truth for stack image tags) |

## File layout (as verified)

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
for the browser-validation pipeline.
