---
description: Visual analysis of webpages using the configured Lemonade vision model
---

# mcp-vision-analysis

Analyze webpages visually using the Lemonade vision model (the default model
from `lpb-config show` — never hardcode a model name). Captures screenshots
and sends them to the Lemonade vision API for structured analysis.

## When to Use

- Visual audit of a webpage (layout, content, UI issues)
- Compare visual changes between versions
- Accessibility and visual QA
- Any task requiring "eyes" on a rendered page

## Procedure

### Via agent-browser (Recommended)

```bash
# 1. Open and screenshot
agent-browser open https://example.com
agent-browser screenshot --annotate --full /tmp/page-screenshot.png

# 2. Read the image — Pi's vision model will analyze it
#    (Just pass the image file to the model via read tool)
```

### Via browser-validate.ts (Full Pipeline)

```bash
# Complete validation: navigate → vitals → a11y → screenshot → vision model
npx tsx /opt/pi-support/browser-validate.ts https://example.com
```

### Via MCP (chrome-devtools, disabled by default)

```json
// ~/.pi/agent/mcp.json
"chrome-devtools": {
  "command": "chrome-devtools-mcp",
  "args": ["--wsEndpoint", "ws://127.0.0.1:9222", "--experimentalVision"],
  "disabled": true
}
```

## Output

- Structured JSON report with metrics and check results
- Annotated screenshots with element refs (@e1, @e2, ...)
- Accessibility violations with fix guidance

## Configuration

| Env Var / Setting | Value | Purpose |
|---|---|---|
| `LEMONADE_BASE_URL` | from `lpb-config show` (external host — the `127.0.0.1` env value is a placeholder) | Vision model API |
| `VISION_MODEL` | default model from `lpb-config show` | Vision model ID |
| `AGENT_BROWSER_MAX_OUTPUT` | `4000` | Max chars for snapshot output |

## Pitfalls

- Chrome must be installed (`install-browser.sh`)
- Vision model needs a running Lemonade server
- Large base64 images increase API latency/cost
- Keep sessions isolated with unique `AGENT_BROWSER_SESSION` IDs
- Always close sessions to prevent zombie Chrome processes
