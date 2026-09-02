#!/usr/bin/env python3
"""model_catalog — lemonade model catalog + model-params catalog helper.

Works with the lemonade-pi-plugin's per-model parameter catalog
(lib/model-params.ts). The catalog decides which models the plugin tunes:
a wire model id in the catalog gets its budgets/sampling/off-switch token;
everything else passes through with default pi behavior.

Commands:
  list      Wire model IDs from the lemonade server (/api/v1/models) —
            the EXACT key to use in the catalog file.
  card      Online-lookup hints for a model's vendor card (checkpoint repo,
            candidate URLs, search terms for the Exa MCP step).
  entry     Build a single catalog entry from CLI flags; print it or merge
            it into the user file. Quick single-model edits.
            Flags: --max-tokens (ceiling), --budgets, --thinking, --coding,
            --non-thinking, --no-think-suffix.
  merge     Merge a catalog-shaped JSON file (one or MANY models) into the
            user file — the preferred multi-model population path.
  effective Print the RESOLVED merged catalog (user tier over plugin tier)
            per model — exactly what the plugin's tuning hook will use.
  validate  Shape-check a catalog file and print a resolution preview.

Env:
  LEMONADE_BASE_URL / LPB_LEMONADE_BASE_URL   server base (or --server)
  LPB_MODEL_PARAMS_FILE                       user catalog path override

Stdlib only. Examples:
  model_catalog.py list
  model_catalog.py card Qwen3.8-27B-GGUF
  model_catalog.py entry "My-Model-8B" --thinking '{"temperature":0.7,"top_p":0.8,"top_k":20,"min_p":0.0,"presence_penalty":0.0,"repetition_penalty":1.0}' --no-think-suffix "" --merge
  model_catalog.py validate
"""
import argparse
import json
import os
import re
import sys
import urllib.request

USER_FILE_DEFAULT = os.path.expanduser("~/.pi/agent/model-params.json")
PLUGIN_FILE_DEFAULT = os.path.expanduser(
    "~/.pi/agent/git/github.com/lpb-stack/lemonade-pi-plugin/lib/model-params.json"
)

SAMPLING_KEYS = {
    "temperature", "top_p", "top_k", "min_p",
    "presence_penalty", "repetition_penalty", "frequency_penalty",
    "repeat_penalty", "mirostat", "mirostat_tau", "mirostat_eta", "dynamic",
}
BUDGET_KEYS = ("minimal", "low", "medium", "high")


def warn(msg):
    print(f"  warning: {msg}", file=sys.stderr)


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def user_file():
    return os.environ.get("LPB_MODEL_PARAMS_FILE", "").strip() or USER_FILE_DEFAULT


def load_json_file(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError) as e:
        warn(f"{path}: unreadable/invalid ({e}) — ignored")
        return None


def server_url_arg(args):
    return (getattr(args, "server", None)
            or os.environ.get("LEMONADE_BASE_URL")
            or os.environ.get("LPB_LEMONADE_BASE_URL") or "").rstrip("/")


def server_api_base(url):
    """llama.cpp server API base from a user-supplied base (may carry /v1)."""
    return url[:-3] if url.endswith("/v1") else url


def fetch_server_models(url):
    url = (url or os.environ.get("LEMONADE_BASE_URL")
           or os.environ.get("LPB_LEMONADE_BASE_URL") or "").rstrip("/")
    if not url:
        die("no server URL — pass --server or set LEMONADE_BASE_URL "
            "(check: lpb-config show)")
    base = server_api_base(url)
    api_key = (os.environ.get("LEMONADE_API_KEY")
               or os.environ.get("LPB_LEMONADE_API_KEY"))
    try:
        data = fetch_json(f"{base}/api/v1/models", api_key)
    except Exception as e:
        die(f"cannot reach {base}/api/v1/models: {e} — check the server URL "
            "(`lpb-config show` is the source of truth)")
    items = data.get("data") if isinstance(data, dict) else None
    return items if isinstance(items, list) else []


def fetch_json(url, api_key=None, timeout=10):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def is_think_heuristic(m):
    text = " ".join([
        m.get("id") or "", m.get("name") or "", m.get("recipe") or "",
        " ".join(m.get("labels") or []),
    ]).lower()
    tokens = ["qwen3", "qwq", "deepseek-r1", "r1-gguf", "think", "reason"]
    return any(t in text for t in tokens)


def ctx_of(m):
    ro = m.get("recipe_options") or {}
    return ro.get("ctx_size") or m.get("max_context_window") \
        or (m.get("config") or {}).get("max_context_window") or None


def cmd_list(args):
    url = server_url_arg(args)
    models = fetch_server_models(url)
    if not models:
        die("server returned no models")
    user = load_json_file(user_file()) or {}
    plugin = load_json_file(PLUGIN_FILE_DEFAULT) or {}
    print(f"{'ID (catalog key)':38} {'ctx':>8} {'max':>7}  think?  catalog      checkpoint")
    print("-" * 100)
    for m in sorted(models, key=lambda x: (x.get("id") or "")):
        mid = m.get("id") or "?"
        tags = []
        if mid in user:
            tags.append("user")
        if mid in plugin:
            tags.append("plugin")
        tag = ",".join(tags) if tags else "-"
        merged = merge_entry(plugin.get(mid) or {}, user.get(mid) or {})
        mt = merged.get("maxTokens", "-")
        print(f"{mid:38} {str(ctx_of(m) or '-'):>8} {str(mt):>7}  "
              f"{'yes' if is_think_heuristic(m) else 'no ':5}  {tag:10}  "
              f"{m.get('checkpoint') or '-'}")
    print(f"\n{len(models)} models — server: {server_api_base(url)}")
    print("catalog: user file:", user_file(), "(exists:", os.path.exists(user_file()), ")")
    print("catalog: plugin file:", PLUGIN_FILE_DEFAULT)
    print("think? is a NAME HEURISTIC (qwen3/qwq/r1/think/reason) — verify with the model card.")


def cmd_card(args):
    models = fetch_server_models(args.server) if not args.checkpoint else []
    m = next((x for x in models if (x.get("id") or "") == args.model), None)
    if m is None and not args.checkpoint:
        ids = [x.get("id") for x in models]
        die(f"model id '{args.model}' not on the server. IDs: {', '.join(filter(None, ids))}")
    checkpoint = args.checkpoint or (m or {}).get("checkpoint") or ""
    repo = checkpoint.split(":")[0] if checkpoint else ""
    base = repo.split("/")[1] if "/" in repo else repo
    base_name = re.sub(r"[-_ ]?(gguf|gptq|awq|imatrix|UD-?Q?\w+|Q\d_?\w*)$",
                       "", base, flags=re.I)
    print(f"model id (catalog key): {args.model}")
    print(f"checkpoint:             {checkpoint or '-'}")
    if repo:
        print(f"checkpoint repo URL:    https://huggingface.co/{repo}")
    print()
    print("Next step (skill): find the OFFICIAL model card, not the quantization repo:")
    name = (m or {}).get("name") or args.model
    print(f"  1. Exa search: \"{base_name or name} model card recommended sampling parameters\"")
    print(f"  2. Likely official card: HF <org>/{base_name or name} "
          f"(find the vendor org via Exa search — quantization repos are NOT the card)")
    print("  Extract per mode: thinking (general), coding (if any), non-thinking:")
    print("    temperature / top_p / top_k / min_p / presence_penalty / repetition_penalty")
    print("  Plus: thinking budget guidance (per level if given) and the model-native")
    print("  off-switch token (e.g. /no_think) if the model supports one.")


def parse_section(value, name):
    if value is None:
        return None
    try:
        sec = json.loads(value)
    except json.JSONDecodeError as e:
        die(f"--{name} is not valid JSON: {e}")
    if not isinstance(sec, dict) or not sec:
        die(f"--{name} must be a non-empty JSON object")
    for k, v in sec.items():
        if k not in SAMPLING_KEYS:
            warn(f"--{name}: unknown key '{k}' (not a known llama.cpp sampling field)")
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            die(f"--{name}.{k} must be a number, got {v!r}")
    return sec


def parse_budgets(value):
    if value is None:
        return None
    try:
        b = json.loads(value)
    except json.JSONDecodeError as e:
        die(f"--budgets is not valid JSON: {e}")
    if not isinstance(b, dict) or not b:
        die("--budgets must be a non-empty JSON object")
    out = {}
    for k, v in b.items():
        if k not in BUDGET_KEYS:
            die(f"--budgets: unknown level '{k}' (allowed: {', '.join(BUDGET_KEYS)})")
        if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
            die(f"--budgets.{k} must be a positive integer, got {v!r}")
        out[k] = v
    return out


def merge_entry(prev, entry):
    """Merge `entry` over `prev` per section, then per field — the same
    semantics as lib/model-params.ts resolveModelEntry (user wins)."""
    merged = {}
    for section in ("budgets", "thinking", "coding", "nonThinking"):
        if section in prev or section in entry:
            merged[section] = {**prev.get(section, {}), **entry.get(section, {})}
    if "noThinkSuffix" in entry or "noThinkSuffix" in prev:
        merged["noThinkSuffix"] = entry.get("noThinkSuffix", prev.get("noThinkSuffix"))
    if "maxTokens" in entry or "maxTokens" in prev:
        merged["maxTokens"] = entry.get("maxTokens", prev.get("maxTokens"))
    return merged


def check_entry(mid, e):
    """Validate one entry. Returns (problems, rendered columns)."""
    problems = []
    if not isinstance(e, dict):
        return [f"{mid}: entry must be an object"], ("ERROR", "-", "-", "-", "-")

    def row(sec, numeric):
        v = e.get(sec)
        if v is None:
            return "-"
        if not isinstance(v, dict):
            problems.append(f"{mid}.{sec}: must be an object")
            return "ERR"
        for k, val in v.items():
            bad = not isinstance(val, (int, float)) or isinstance(val, bool)
            if numeric == "budgets" and (k not in BUDGET_KEYS
                                         or not isinstance(val, int) or val <= 0):
                bad = True
            if bad:
                problems.append(f"{mid}.{sec}.{k}: invalid")
        return json.dumps(v)

    mt = e.get("maxTokens")
    if mt is not None and (not isinstance(mt, int) or isinstance(mt, bool) or mt <= 0):
        problems.append(f"{mid}.maxTokens: must be a positive integer, got {mt!r}")
        mt_disp = "ERR"
    else:
        mt_disp = str(mt) if mt is not None else "-"

    budgets_sec = e.get("budgets")
    if budgets_sec is None:
        budgets = "-"
    elif not isinstance(budgets_sec, dict):
        row("budgets", "budgets")
        budgets = "ERR"
    else:
        row("budgets", "budgets")  # validates keys + positive ints
        budgets = " ".join(f"{k}={budgets_sec[k]}" for k in BUDGET_KEYS
                           if k in budgets_sec) or "-"
    thinking = row("thinking", "s")
    coding = row("coding", "s") if isinstance(e.get("coding"), dict) else None
    non_t = row("nonThinking", "s")
    suffix = e.get("noThinkSuffix")
    if suffix is not None and not isinstance(suffix, str):
        problems.append(f"{mid}.noThinkSuffix: must be a string")
        suffix = "ERR"
    if suffix is None:
        suffix_disp = "/no_think (default)"
    elif suffix == "":
        suffix_disp = "(none — disabled)"
    else:
        suffix_disp = suffix
    return problems, (mt_disp, budgets, thinking, coding, non_t, suffix_disp)


def effective_catalog(plugin, user):
    """Resolved merged catalog — mirror of resolveModelEntry. Returns
    {model: (entry, origin)} for the union of both tiers."""
    out = {}
    for mid in sorted(set(plugin or {}) | set(user or {})):
        base = (plugin or {}).get(mid)
        over = (user or {}).get(mid)
        if base is None and over is None:
            continue
        origin = "user+plugin" if (base and over) else ("user" if over is not None else "plugin")
        out[mid] = (merge_entry(base or {}, over or {}), origin)
    return out


def print_entry_table(resolved, show_origin=True):
    """Print (entry, origin-or-None) pairs as a table; returns problem count."""
    errors = 0
    if show_origin:
        print(f"{'model':38} {'src':11} {'max':>7}  budgets              thinking            nonThinking  suffix")
    else:
        print(f"{'model':38} {'max':>7}  budgets              thinking            nonThinking  suffix")
    print("-" * 118)
    for mid, (e, origin) in resolved.items():
        problems, (mt_disp, budgets, thinking, coding, non_t, suffix) = check_entry(mid, e)
        errors += len(problems)
        for p in problems:
            print(f"  {p}")
        if show_origin:
            print(f"{mid:38} {origin or '-':11} {mt_disp:>7}  {budgets:20} {thinking or '-':18} {non_t or '-':12}  {suffix}")
            if coding:
                print(f"{'':38} {'':11} {'':>7}  coding: {coding}")
        else:
            print(f"{mid:38} {mt_disp:>7}  {budgets:20} {thinking or '-':18} {non_t or '-':12}  {suffix}")
            if coding:
                print(f"{'':38} {'':>7}  coding: {coding}")
    return errors


def cmd_entry(args):
    entry = {}
    if args.max_tokens is not None:
        if not isinstance(args.max_tokens, int) or args.max_tokens <= 0:
            die("--max-tokens must be a positive integer")
        entry["maxTokens"] = args.max_tokens
    budgets = parse_budgets(args.budgets)
    if budgets:
        entry["budgets"] = budgets
    thinking = parse_section(args.thinking, "thinking")
    if thinking:
        entry["thinking"] = thinking
    coding = parse_section(args.coding, "coding")
    if coding:
        entry["coding"] = coding
    non_thinking = parse_section(args.non_thinking, "non-thinking")
    if non_thinking:
        entry["nonThinking"] = non_thinking
    if args.no_think_suffix is not None:
        entry["noThinkSuffix"] = args.no_think_suffix
    if not entry:
        die("nothing to do — pass at least one of --max-tokens/--budgets/"
            "--thinking/--coding/--non-thinking/--no-think-suffix")

    if args.merge is None:
        print(json.dumps({args.model: entry}, indent=2))
        print(f"# merge with:  {sys.argv[0]} entry {args.model!r} ... --merge [FILE]",
              file=sys.stderr)
        return

    path = args.merge
    cat = load_json_file(path)
    if cat is None:
        cat = {}
    if not isinstance(cat, dict):
        die(f"{path}: top level must be a JSON object")
    cat[args.model] = merge_entry(cat.get(args.model) or {}, entry)
    with open(path, "w") as f:
        json.dump(cat, f, indent=2)
        f.write("\n")
    print(f"merged into {path}:")
    print(json.dumps({args.model: cat[args.model]}, indent=2))
    print("applies on the NEXT request (mtime-checked) — no pi restart needed.")


def cmd_merge(args):
    src = load_json_file(args.file)
    if src is None:
        die(f"{args.file}: not found or invalid JSON")
    if not isinstance(src, dict):
        die(f"{args.file}: top level must be a JSON object of model entries")
    for mid, e in src.items():
        if not isinstance(e, dict):
            die(f"{args.file}: entry for {mid!r} must be an object")
    target = args.target or user_file()
    cat = load_json_file(target)
    if cat is None:
        cat = {}
    if not isinstance(cat, dict):
        die(f"{target}: top level must be a JSON object")
    for mid in sorted(src):
        cat[mid] = merge_entry(cat.get(mid) or {}, src[mid])
    if args.dry_run:
        print(f"would merge {len(src)} model(s) from {args.file} into {target}:")
        for mid in sorted(src):
            print(json.dumps({mid: cat[mid]}, indent=2))
        return
    with open(target, "w") as f:
        json.dump(cat, f, indent=2)
        f.write("\n")
    print(f"merged {len(src)} model(s) from {args.file} into {target}:")
    for mid in sorted(src):
        print(f"  {mid}")
    print("run: validate + effective  ·  applies on the NEXT request (no pi restart)")


def cmd_effective(args):
    plugin = load_json_file(PLUGIN_FILE_DEFAULT) or {}
    user = load_json_file(user_file()) or {}
    resolved = {mid: (e, o) for mid, (e, o) in effective_catalog(plugin, user).items()}
    print_entry_table(resolved)
    print()
    print(f"user file:    {user_file()} (exists: {os.path.exists(user_file())})")
    print(f"plugin file:  {PLUGIN_FILE_DEFAULT}")
    print("this is exactly what the tuning hook resolves (user tier wins per field).")


def cmd_validate(args):
    path = args.file
    if path is None:
        path = PLUGIN_FILE_DEFAULT if args.plugin else user_file()
    cat = load_json_file(path)
    if cat is None:
        if args.plugin:
            die(f"plugin catalog missing: {path}")
        print(f"ok: {path} does not exist (optional user tier — nothing to validate)")
        return
    if not isinstance(cat, dict):
        die(f"{path}: top level must be a JSON object (got {type(cat).__name__})")
    resolved = {mid: (e, None) for mid, e in sorted(cat.items())}
    errors = print_entry_table(resolved, show_origin=False)
    print()
    if errors:
        die(f"{errors} problem(s) in {path}")
    print(f"ok: {len(cat)} model(s) in {path}")


def main():
    ap = argparse.ArgumentParser(description="lemonade model catalog + model-params helper",
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--server", help="lemonade server base URL (default: LEMONADE_BASE_URL)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="wire model IDs from the server")

    p = sub.add_parser("card", help="online-lookup hints for a model's vendor card")
    p.add_argument("model", help="wire model id (see `list`)")
    p.add_argument("--checkpoint", help="skip the server; give the checkpoint ref directly")

    p = sub.add_parser("entry", help="build/merge a catalog entry")
    p.add_argument("model", help="wire model id (catalog key)")
    p.add_argument("--max-tokens", type=int,
                   help="response ceiling (max_completion_tokens) in tokens — exact value, "
                        "applied at model sync (needs pi restart or re-sync to take effect)")
    p.add_argument("--budgets", help='JSON, e.g. \'{"minimal":2048,"low":3072,"medium":8192,"high":16384}\'')
    p.add_argument("--thinking", help='JSON sampling row, e.g. \'{"temperature":1.0,"top_p":0.95,"top_k":20,"min_p":0.0,"presence_penalty":0.0,"repetition_penalty":1.0}\'')
    p.add_argument("--coding", help="JSON coding-profile row (merged over --thinking)")
    p.add_argument("--non-thinking", help="JSON off-level sampling row")
    p.add_argument("--no-think-suffix", default=None,
                   help="off-switch token; empty string disables for this model; omit = default /no_think")
    p.add_argument("--merge", nargs="?", const=USER_FILE_DEFAULT, default=None,
                   metavar="FILE", help="merge into FILE (default: the user catalog)")

    p = sub.add_parser("merge", help="merge a catalog-shaped JSON file (1..N models) into the catalog")
    p.add_argument("file", help='JSON file: {"<model id>": {"budgets": {...}, "thinking": {...}, ...}}')
    p.add_argument("target", nargs="?", help="target file (default: the user catalog)")
    p.add_argument("--dry-run", action="store_true",
                   help="print the resulting merged entries without writing")

    p = sub.add_parser("effective", help="resolved merged catalog (user over plugin) — what the hook sees")

    p = sub.add_parser("validate", help="shape-check + resolution preview")
    p.add_argument("file", nargs="?", help="catalog file (default: user file)")
    p.add_argument("--plugin", action="store_true", help="validate the plugin-shipped catalog")

    args = ap.parse_args()
    {"list": cmd_list, "card": cmd_card, "entry": cmd_entry, "merge": cmd_merge,
     "effective": cmd_effective, "validate": cmd_validate}[args.cmd](args)


if __name__ == "__main__":
    main()
