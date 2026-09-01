---
description: Tune lemonade-served models — exact wire IDs from the server catalog, vendor-recommended parameters from online model cards, the per-model parameter file, and wire verification.
---

# lemonade-model-params

Manage the lemonade-pi-plugin's per-model parameter catalog: fetch the exact
model id from the server, fetch vendor-recommended settings (sampling,
budgets, off-switch token) from online model cards, write catalog entries,
and verify what is actually sent over the wire.

## When to Use

- Adding a new lemonade-served model to payload tuning (P2 budget / P3
  sampling / P5 off-switch)
- Finding the exact wire model id (the catalog key)
- Finding a model's vendor-recommended sampling parameters (model card)
- Debugging what the plugin sends (`LPB_PAYLOAD_DEBUG`)

## Background (30 seconds)

The plugin's `before_provider_request` hook tunes **catalogued models only**:
the wire `payload.model` id must exist in the user catalog
(`~/.pi/agent/model-params.json`) or the plugin catalog
(`lemonade-pi-plugin/lib/model-params.json`). Uncatalogued → default pi
behavior. Precedence per field: wire payload fields (pi `samplingParams`
etc.) > user tier > plugin tier — the catalog only fills missing fields.
Editing the user file applies on the **next request** (mtime-checked, no pi
restart). Full design: `lemonade-pi-plugin/docs/qwen-thinking-mainstream-pi.md`
§5.0.

## Tool

`scripts/model_catalog.py` (resolve against this skill's directory; stdlib
only). Server URL: `--server` or `LEMONADE_BASE_URL` env (see `lpb-config show`).

```bash
S=<skill dir>/scripts/model_catalog.py
python3 $S list        # wire IDs + ctx + think-heuristic + catalog status
python3 $S card <id>   # checkpoint repo + online card search hints
python3 $S entry <id> --thinking '{...}' ... [--merge [FILE]]
python3 $S validate [--plugin] [FILE]
```

## Procedure

### 1. Get the exact wire id

`python3 $S list` — the `ID (catalog key)` column is the exact catalog key
(server `id` = wire `payload.model`). Note the `checkpoint` (HF repo pointer
for the card search) and whether the model is already catalogued.

### 2. Fetch vendor settings online (Exa MCP)

Run `python3 $S card <id>` for the hints, then use exa:

- Search the **official** model card (vendor org HF page / vendor docs — not
  the quantization repo), e.g. `"<base name> model card recommended sampling
  parameters"`.
- Fetch the card (exa content) and extract, per mode — thinking (general),
  coding (if listed), non-thinking:
  `temperature / top_p / top_k / min_p / presence_penalty / repetition_penalty`.
- Also extract: per-level thinking budget guidance (if given) and any
  model-native off-switch token (Qwen3.x hybrids: `/no_think`; other
  families may differ or have none).
- Cite the source in your summary. If sibling model cards disagree, follow
  the **served model's** card and note the discrepancy.

### 3. Build + merge the entry

Dry-run first (no `--merge`) and review the JSON:

```bash
python3 $S entry "<id>" \
  --budgets '{"minimal":2048,"low":3072,"medium":8192,"high":16384}' \
  --thinking '{"temperature":1.0,"top_p":0.95,"top_k":20,"min_p":0.0,"presence_penalty":0.0,"repetition_penalty":1.0}' \
  --non-thinking '{"temperature":0.7,"top_p":0.8,"top_k":20,"min_p":0.0,"presence_penalty":1.5,"repetition_penalty":1.0}' \
  --no-think-suffix "/no_think" \
  --merge
```

`--merge` (default file `~/.pi/agent/model-params.json`) merges per
section/field; applies on the next request — no pi restart.

### 4. Validate + wire verification

- `python3 $S validate` — shape check + resolution preview (budgets, rows,
  suffix).
- Wire proof: set `LPB_PAYLOAD_DEBUG=1` in the devstack `.env`, **restart
  pi**, send one prompt at a thinking level and one at off, then inspect
  `/tmp/pi-payload-capture.jsonl`: lines for the model must show the
  catalog's budget + sampling fields, and `no_think: true` at the off level.
  Uncatalogued models show the raw view.

### 5. (Optional) Promote to the plugin tier

If the model is the one the stack serves, propose moving the entry into
`lemonade-pi-plugin/lib/model-params.json` (versioned with the stack) and
commit/push on `lpb-dev` — with explicit user approval.

## Pitfalls

- The catalog key is the server `id` (wire `payload.model`) — NOT the HF
  repo name, NOT the checkpoint.
- The quantization repo's page (unsloth etc.) is not the vendor card — use
  the official model's card for recommended values.
- Fields already present in the wire payload (pi `samplingParams`, user
  config) always beat the catalog; don't "fix" a mismatch by fighting pi.
- Never edit `~/.pi/agent/models-store.json` (pi-managed store; the plugin
  only syncs its `lemonade` model list there).
- `think?` in `list` is a name heuristic — verify thinking support in the
  card before assuming a budget row matters.
- QWEN_* env vars are retired: use `LPB_PAYLOAD_TUNING` (master),
  `LPB_SAMPLING_PROFILE`, `LPB_NO_THINK_SUFFIX`, `LPB_MODEL_PARAMS_FILE`,
  `LPB_PAYLOAD_DEBUG` (all `LPB_*` in devstack `.env` are promoted by
  start.sh; restart pi for env changes).
- Non-Qwen models: the DEFAULT off-switch token is Qwen's `/no_think` —
  pass `--no-think-suffix ""` (or the model's documented token) unless the
  card documents one.

## Verification

- `validate` exits 0 and the preview shows the expected rows/suffix.
- With `LPB_PAYLOAD_DEBUG=1`, the capture file shows the catalogued model's
  tuned view (budget + sampling fields present) and the raw view for
  uncatalogued models.
- Budget clamp check: wire `thinking_budget_tokens` =
  min(catalog level value, `max_completion_tokens` − 1024).
