---
description: Automated browser validation pipeline with JSON report generation
---

# browser-validation

Automated browser validation pipeline — navigate, snapshot, screenshot, vitals, a11y, vision model analysis, structured JSON report.

## When to Use

- Validate a web page's structure, performance, and accessibility
- CI/CD browser tests with structured JSON output
- Vision model analysis of web pages (screenshot + pre-computed data)
- Subagent browser tests with retry/repair loop

## Procedure

### Quick Validation (CLI)

```bash
# One-shot validation with vision model
npx tsx /opt/pi-support/browser-validate.ts https://example.com
```

### As a Subagent Task

```bash
# Generate unique session ID
SESSION_ID=$(npx tsx /opt/pi-support/session-uuid.ts "${PI_WORKTREE_ID}-validate")

# Run the full pipeline
npx tsx /opt/pi-support/browser-validate.ts \
  https://example.com \
  --session "$SESSION_ID" \
  --attempts 3
```

### Manual Step-by-Step

```bash
# 1. Navigate
agent-browser --session "$SESSION_ID" open https://example.com

# 2. Collect metrics
VITALS=$(agent-browser --session "$SESSION_ID" vitals --json)
A11Y=$(agent-browser --session "$SESSION_ID" a11y --json)
SNAPSHOT=$(agent-browser --session "$SESSION_ID" snapshot -i)

# 3. Screenshot with annotated refs
agent-browser --session "$SESSION_ID" screenshot --annotate \
  /browser-states/${SESSION_ID}/screenshot.png

# 4. Close session
agent-browser --session "$SESSION_ID" close
```

## Output

Validated report saved to `/browser-states/<session-id>/validated.json`

```json
{
  "url": "https://example.com",
  "status": "PASS",
  "metrics": { "lcp_ms": 120, "cls": 0.01, "ttfb_ms": 45, "a11y_violations": 0, "a11y_passes": 15 },
  "checks": [ ... ]
}
```

## Configuration

| Env Var / Setting | Value | Purpose |
|---|---|---|
| `LEMONADE_BASE_URL` | from `lpb-config show` (external host — the `127.0.0.1` env value is a placeholder) | Vision model API |
| `VISION_MODEL` | default model from `lpb-config show` | Vision model ID |

## Pitfalls

- **Chrome not installed**: Run `bash /opt/pi-support/install-browser.py` first if Chrome is missing
- **Zombie processes**: Always close the session when done (`agent-browser --session <id> close`)
- **Vision model timeout**: The retry loop handles JSON parsing failures (max 3 attempts)
- **Base64 image size**: Large screenshots increase API cost and latency
