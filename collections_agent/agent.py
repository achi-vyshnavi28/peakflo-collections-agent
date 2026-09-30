"""Three agents on one call turn:
research (Python tool, facts.lookup) -> collections agent (LLM, speaks) -> editor agent (LLM, self-reflection review)
-> at most one rewrite if the editor finds a problem."""
import json
from pathlib import Path

from .facts import _below_hundred, lookup
from .llm import chat

PROMPTS = Path(__file__).resolve().parents[1] / "prompts"

EDITOR = """You are a QA reviewer for a phone collections agent. The draft below will be spoken aloud to the customer.

FACTS the agent is allowed to use:
{facts}

The customer said: "{says}"
Draft reply: "{draft}"

Check the draft for these problems:
1. It states an amount or date that is not exactly in FACTS, or does arithmetic of its own.
2. It threatens the customer or mentions legal action, courts, police, credit scores or penalties.
3. It pushes for payment when the customer disputes the amount, says they already paid, asks to stop calling, or is busy.
4. It shares amounts or invoice details with someone who is not {contact}.
5. It is not speakable: digits, currency symbols, lists, links, or more than about 40 words.
6. It ignores what the customer actually said, or promises a discount or fee waiver.

Return JSON only: {{"ok": true or false, "problems": ["short description", ...]}}"""


def opening(f):
    return f"Hello, this is {f['agent_name']} calling from {f['supplier']}. Am I speaking with {f['contact']}?"


def system_prompt(version, f):
    template = (PROMPTS / {"v1": "v1_basic.txt", "v2": "v2_voice.txt"}[version]).read_text(encoding="utf-8")
    plans = "; ".join(f"{p['instalments']} payments of {p['each_spoken']}" for p in f["plans"])
    return template.format(
        **f, days_overdue_spoken=_below_hundred(f["days_overdue"]), plans_line=plans,
        paid_line=f"\n- Already paid: {f['paid_spoken']}" if f["paid"] else "")


def respond(scenario, config, model=None):
    """config: 'v1', 'v2' or 'v2_reflect'. Returns the spoken reply plus a trace of each agent's step."""
    f = lookup(scenario["account"])
    version = "v1" if config == "v1" else "v2"
    messages = [{"role": "system", "content": system_prompt(version, f)},
                {"role": "assistant", "content": opening(f)},
                {"role": "user", "content": scenario["says"]}]
    kw = {"model": model} if model else {}
    draft = chat(messages, **kw)
    trace = {"research": {k: f[k] for k in ("balance", "due_date", "plans")}, "draft": draft}
    if config != "v2_reflect":
        return draft, trace

    facts_block = system_prompt("v2", f).split("FACTS")[1].split("RULES")[0].strip()
    raw = chat([{"role": "user", "content": EDITOR.format(facts=facts_block, says=scenario["says"], draft=draft,
                                                           contact=f["contact"])}], json_mode=True, **kw)
    try:
        review = json.loads(raw)
    except json.JSONDecodeError:
        review = {"ok": True, "problems": [], "parse_error": raw[:200]}
    trace["editor"] = review
    if review.get("ok", True) or not review.get("problems"):
        return draft, trace
    fix = messages + [{"role": "assistant", "content": draft},
                      {"role": "user", "content": "[Internal reviewer, not the customer] Rewrite your last reply to fix: "
                                                  + "; ".join(review["problems"])
                                                  + ". Reply with only the corrected words to speak."}]
    final = chat(fix, **kw)
    trace["rewrite"] = final
    return final, trace
