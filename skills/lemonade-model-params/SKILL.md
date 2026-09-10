---
description: Tune lemonade-served models — exact wire IDs from the server catalog, vendor-recommended parameters from online model cards, the per-model parameter file, and wire verification.
---

# lemonade-model-params

Manage the lemonade-pi-plugin's per-model parameter catalog: fetch the exact
model id from the server, fetch vendor-recommended settings (sampling,
budgets, offParams (wire off-switch)) from online model cards, write catalog entries,
and verify what is actually sent over the wire.

## When to Use

- Adding a new lemonade-served model to payload tuning (P2 budget / P3
  sampling / P5 off-switch)
- Setting a model's response ceiling (`maxTokens` — exact tokens, no ratio)
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
restart) — **except `maxTokens`**, the response ceiling, which is applied at
**model sync**: a ceiling change needs a pi restart (or model re-sync) to
take effect. Full design:
`lemonade-pi-plugin/docs/qwen-thinking-mainstream-pi.md` §5.0.

## Tool

`scripts/model_catalog.py` (resolve against this skill's directory; stdlib
only). Server URL: `--server` or `LEMONADE_BASE_URL` env (see `lpb-config show`).

```bash
S=<skill dir>/scripts/model_catalog.py
python3 $S list        # wire IDs + ctx + maxTokens + think-heuristic + catalog status
python3 $S card <id>   # checkpoint repo + online card search hints
python3 $S entry <id> --max-tokens 16384 --thinking '{...}' ... [--merge [FILE]]   # single-model quick edit
python3 $S merge FILE  # merge a catalog-shaped JSON file (1..N models) → user catalog (--dry-run first)
python3 $S effective   # resolved merged catalog (user over plugin) — what the hook sees
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
- Also extract: per-level thinking budget guidance (if given), the
  recommended **max output length** (feeds the `maxTokens` ceiling — for
  Qwen thinking models the stack standard is 16384, i.e. the high-level
  budget), and whether the model has a per-request thinking flag (Qwen
  hybrids: `enable_thinking`) — that becomes the `offParams` row.
- Cite the source in your summary. If sibling model cards disagree, follow
  the **served model's** card and note the discrepancy.

### 3. Build + merge the entries

**Multiple models (preferred)** — write ONE catalog-shaped JSON file (clean,
reviewable, no shell-quoting), then a single merge:

```json
{
  "Model-A": { "maxTokens": 16384,
               "budgets": {"minimal":2048,"low":3072,"medium":8192,"high":16384},
               "thinking": {"temperature":1.0,"top_p":0.95,"top_k":20,"min_p":0.0,"presence_penalty":0.0,"repetition_penalty":1.0},
               "nonThinking": {"temperature":0.7,"top_p":0.8,"top_k":20,"min_p":0.0,"presence_penalty":1.5,"repetition_penalty":1.0} },
  "Model-B": { "nonThinking": {"temperature":0.9,"top_p":0.95} }
}
```

```bash
python3 $S merge entries.json --dry-run   # review the merged result first
python3 $S merge entries.json             # → user catalog (default target)
```

Merge is per section/field and never drops existing models. Review the JSON
before merging (it IS the catalog shape — what you write is what gets read).

**Single-model quick edit** — dry-run first (no `--merge`) and review the
JSON, then merge:

```bash
python3 $S entry "<id>" \
  --max-tokens 16384 \
  --budgets '{"minimal":2048,"low":3072,"medium":8192,"high":16384}' \
  --thinking '{...}' --non-thinking '{...}' \
  --off-params '{"enable_thinking": false}' \
  --merge
```

**Non-thinking / non-Qwen models** — omit `budgets` entirely, put the card's
sampling in `nonThinking` (the row the plugin applies when pi sends no
thinking fields; mirror it in `thinking` if the card also documents a
reasoning mode). If the model has a per-request thinking flag, add
`"offParams": {"enable_thinking": false}` — the P5 wire off-switch; without
it, level `off` sends nothing and the model reasons at its own length.
(`noThinkSuffix` is retired — the plugin dropped it in 59c6537.)

`--merge` / `merge` apply on the **next request** (mtime-checked) — no pi
restart.

### 4. Validate + wire verification

- `python3 $S effective` — the RESOLVED merged catalog (user over plugin,
  per model: origin + rows + suffix). This is exactly what the tuning hook
  will use; check it right after merging.
- `python3 $S validate` — shape check of one tier (user by default,
  `--plugin` for the shipped tier).
- Wire proof: set `LPB_PAYLOAD_DEBUG=1` in the devstack `.env`, **restart
  pi**, send one prompt at a thinking level and one at off, then inspect
  `/tmp/pi-payload-capture.jsonl`: lines for the model must show the
  catalog's budget + sampling fields, and `enable_thinking: false` at the
  off level (the offParams row). Uncatalogued models show the raw view.

### 5. (Optional) Promote to the plugin tier

If the model is the one the stack serves, propose moving the entry into
`lemonade-pi-plugin/lib/model-params.json` (versioned with the stack) and
commit/push on `lpb-dev` — with explicit user approval.

## Pitfalls

- `maxTokens` is a **sync-time** field: budgets/sampling/suffix apply on the
  next request (mtime), but a ceiling change needs a pi restart or model
  re-sync. Verify the ceiling via the `max_completion_tokens` value in a
  `LPB_PAYLOAD_DEBUG` capture AFTER the restart.
- Ceilings are exact token values per model — there is no ratio (the
  `LPB_MAX_TOKENS_CONTEXT_RATIO` env chain and the 0.06/0.125 formula were
  retired 2026-09-02). Pick the number from the model card's max output
  guidance; the server's `prompt + max_tokens ≤ n_ctx` preflight is the
  overflow guard, so an over-pinned ceiling fails loudly, not silently.
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
  `LPB_SAMPLING_PROFILE`, `LPB_MODEL_PARAMS_FILE`,
  `LPB_PAYLOAD_DEBUG` (all `LPB_*` in devstack `.env` are promoted by
  start.sh; restart pi for env changes).
- The off switch is the catalog `offParams` row (P5) — a wire field, NOT a
  prompt suffix. `noThinkSuffix` was dropped from the plugin (59c6537); the
  skill tool warns if you still pass `--no-think-suffix`. For families
  without a per-request flag, omit `offParams` (off level then sends no
  thinking fields — verified behavior, e.g. Gemma 4, whose `<|think|>`
  ON-token is a system-prefix, not an off field).
- `exa_web_fetch_exa` truncates long HF READMEs (cut off ~2KB, often before
  the sampling section) — fall back to `curl https://huggingface.co/<org>/<model>/raw/main/README.md`
  or rely on search highlights (which usually carry the sampling block).

## Verification

- `effective` shows every new model with the expected rows/suffix and the
  right origin (user/plugin/user+plugin); `validate` exits 0.
- `list` shows the new models tagged `user`/`plugin`.
- With `LPB_PAYLOAD_DEBUG=1`, the capture file shows the catalogued model's
  tuned view (budget + sampling fields present) and the raw view for
  uncatalogued models.
- Budget clamp check: wire `thinking_budget_tokens` =
  min(catalog level value, `max_completion_tokens` − 1024).
