"""A/B evaluation: prompt v1 vs voice-optimised v2 vs v2 with editor self-reflection, on 30 tricky customer replies.

python run_eval.py                 # all configs, default model
python run_eval.py --model groq/openai/gpt-oss-120b
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from collections_agent.agent import respond
from collections_agent.checks import score
from collections_agent.facts import lookup
from collections_agent.llm import MODEL

ROOT = Path(__file__).resolve().parent
CONFIGS = ["v1", "v2", "v2_reflect"]
METRICS = ["pass", "task", "no_invented_amount", "no_threat", "voice_ready"]


def pct(xs):
    return round(100 * sum(xs) / len(xs)) if xs else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args()
    scenarios = json.loads((ROOT / "data" / "scenarios.json").read_text(encoding="utf-8"))

    rows = []
    for config in CONFIGS:
        for s in scenarios:
            reply, trace = respond(s, config, model=args.model)
            r = score(reply, s, lookup(s["account"]))
            rows.append({"config": config, "id": s["id"], "tag": s["tag"], "says": s["says"], "reply": reply,
                         **{m: r[m] for m in METRICS}, "amounts_said": r["amounts_said"],
                         "rewritten": "rewrite" in trace, "editor": trace.get("editor")})
            print(f"{config:10} {s['id']} {'PASS' if r['pass'] else 'fail'}  {reply[:90]!r}")

    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    slug = args.model.replace("/", "_")
    (out / f"results_{slug}.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    by = defaultdict(list)
    for row in rows:
        by[row["config"]].append(row)
    lines = [f"Model: `{args.model}` · {len(scenarios)} scenarios · temperature 0\n",
             "| Config | All checks pass | Handles the situation | No invented amount | No threat | Voice ready | Rewrites |",
             "|---|---|---|---|---|---|---|"]
    for c in CONFIGS:
        rs = by[c]
        lines.append(f"| {c} | " + " | ".join(f"{pct([x[m] for x in rs])}%" for m in METRICS)
                     + f" | {sum(x['rewritten'] for x in rs)} |")
    lines += ["", "Failures by situation (scenarios failing any check):", "",
              "| Situation | " + " | ".join(CONFIGS) + " |", "|---|" + "---|" * len(CONFIGS)]
    for tag in sorted({r["tag"] for r in rows}):
        cells = []
        for c in CONFIGS:
            t = [x for x in by[c] if x["tag"] == tag]
            cells.append(f"{sum(not x['pass'] for x in t)}/{len(t)}")
        lines.append(f"| {tag} | " + " | ".join(cells) + " |")
    summary = "\n".join(lines)
    (out / f"summary_{slug}.md").write_text(summary + "\n", encoding="utf-8")
    print("\n" + summary)


if __name__ == "__main__":
    main()
