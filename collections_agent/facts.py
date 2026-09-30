"""Research agent: looks up invoice facts with plain Python, so amounts never come from the LLM.

Also holds the Indian-numbering helpers used to speak amounts and to read them back out of replies.
"""
import json
import re
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"

ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
        "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
ORDINALS = {1: "first", 2: "second", 3: "third", 5: "fifth", 8: "eighth", 9: "ninth", 12: "twelfth"}


def _below_hundred(n):
    return ONES[n] if n < 20 else TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])


def _below_thousand(n):
    head, rest = divmod(n, 100)
    parts = ([ONES[head] + " hundred"] if head else []) + ([_below_hundred(rest)] if rest else [])
    return " ".join(parts)


def rupees_in_words(n):
    """120000 -> 'one lakh twenty thousand rupees' (Indian system, as a caller would say it)."""
    n = int(round(n))
    if n == 0:
        return "zero rupees"
    parts = []
    for size, name in ((10**7, "crore"), (10**5, "lakh"), (1000, "thousand")):
        if n >= size:
            parts.append(_below_hundred(n // size) + " " + name)
            n %= size
    if n:
        parts.append(_below_thousand(n))
    return " ".join(parts) + " rupees"


def date_in_words(iso):
    d = date.fromisoformat(iso)
    day = d.day
    if day in ORDINALS:
        spoken = ORDINALS[day]
    elif day < 20:
        spoken = ONES[day] + "th"
    elif day % 10 == 0:
        spoken = TENS[day // 10][:-1] + "ieth"
    else:
        spoken = TENS[day // 10] + " " + ORDINALS.get(day % 10, ONES[day % 10] + "th")
    return f"{spoken} of {MONTHS[d.month - 1]}"


WORD_VALUES = {w: i for i, w in enumerate(ONES)} | {w: 10 * i for i, w in enumerate(TENS) if w}
SCALES = {"hundred": 100, "thousand": 1000, "lakh": 10**5, "lakhs": 10**5, "lac": 10**5, "lacs": 10**5,
          "crore": 10**7, "crores": 10**7}


def _words_to_number(tokens):
    total, current = 0, 0
    for t in tokens:
        if t in WORD_VALUES:
            current += WORD_VALUES[t]
        elif t == "hundred":
            current = max(current, 1) * 100
        elif t in SCALES:
            total += max(current, 1) * SCALES[t]
            current = 0
    return total + current


def amounts_in(text):
    """Every money-sized number (1,000 or more) in a reply, whether written as digits or spoken as words."""
    low = text.lower()
    for odd in (" ", " ", " "):  # narrow and non-breaking spaces models put inside numbers
        low = low.replace(odd, " ")
    for dash in ("‑", "‐", "–", "—"):
        low = low.replace(dash, "-")
    low = re.sub(r"\binv[\s-]*\d+", " ", low)  # invoice numbers are identifiers, not amounts
    low = low.replace("-", " ")
    found = []
    # digits with an Indian or plain scale word: "1.2 lakh", "20 thousand", "38.5k"
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(lakhs?|lacs?|crores?|thousand|k)\b", low):
        scale = {"k": 1000, "thousand": 1000}.get(m.group(2), SCALES.get(m.group(2), 1))
        found.append(round(float(m.group(1)) * scale))
    low = re.sub(r"(\d+(?:\.\d+)?)\s*(lakhs?|lacs?|crores?|thousand|k)\b", " ", low)
    # plain digits: 1,20,000 or 120000 or 38,500
    for m in re.finditer(r"\d[\d,]*(?:\.\d+)?", low):
        found.append(round(float(m.group().replace(",", ""))))
    # spoken: "one lakh twenty thousand five hundred"
    vocab = set(WORD_VALUES) | set(SCALES) | {"and"}
    run = []
    for tok in re.findall(r"[a-z]+", low) + ["."]:
        if tok in vocab and not (tok == "and" and not run):
            run.append(tok)
            continue
        words = [t for t in run if t != "and"]
        if any(t in SCALES for t in words):
            found.append(_words_to_number(words))
        run = []
    return [n for n in found if n >= 1000 and not 2020 <= n <= 2030]


def load_accounts():
    return json.loads((DATA / "invoices.json").read_text(encoding="utf-8"))


def lookup(account_id, db=None):
    """The research agent's tool: facts about one account, with every amount pre-computed and pre-spoken."""
    db = db or load_accounts()
    a = db["accounts"][account_id]
    balance = a["invoice_amount"] - a["paid"]
    plans = [{"instalments": k, "each": round(balance / k), "each_spoken": rupees_in_words(round(balance / k))}
             for k in a["plans"]]
    return {
        "supplier": db["supplier"], "agent_name": db["agent_name"], "company": a["company"], "contact": a["contact"],
        "invoice": a["invoice"], "invoice_amount": a["invoice_amount"], "paid": a["paid"], "balance": balance,
        "balance_spoken": rupees_in_words(balance), "invoice_amount_spoken": rupees_in_words(a["invoice_amount"]),
        "paid_spoken": rupees_in_words(a["paid"]) if a["paid"] else None,
        "due_date": a["due_date"], "due_date_spoken": date_in_words(a["due_date"]),
        "days_overdue": a["days_overdue"], "plans": plans,
    }


def allowed_amounts(facts, extra=()):
    """Amounts the agent may say: anything the research tool returned, plus figures the customer themselves raised."""
    allowed = {facts["invoice_amount"], facts["balance"]} | {p["each"] for p in facts["plans"]} | set(extra)
    if facts["paid"]:
        allowed.add(facts["paid"])
    return allowed
