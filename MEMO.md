# How I'd build and evaluate a collections voice agent for Peakflo

**Achi Vyshnavi** · Forward Deployed Engineer application · Code and results: github.com/achi-vyshnavi28/peakflo-collections-agent

## The problem
A collections agent speaks for Peakflo's customer, to *their* customers, about money. One wrong amount, one threat,
or one balance read out to the wrong person costs trust that no accuracy score shows. So before tuning anything,
I built a way to measure those failures.

## What I built (one day, synthetic data)
- **Three agents per turn.** A Python research tool looks up the invoice and pre-computes every amount and date as
  spoken words. A collections agent replies. An editor agent reviews the draft and triggers one rewrite if needed.
- **30 tricky customer replies** across six accounts: disputes, already paid, hardship, Hinglish, stop calling,
  wrong person on the line, fee-waiver requests, anger, and "what will you do if I don't pay?".
- **Deterministic scoring** that reads every amount back out of the reply (digits or words), plus checks for
  threats, privacy, pressure, speakability and whether the situation was handled.

## Results (gpt-oss-120b, 30 scenarios each)

| Setup | All checks pass | Voice ready | No invented amount |
|---|---|---|---|
| v1: basic prompt | 13% | 17% | 93% |
| v2: voice prompt + facts tool | 93% | 97% | 100% |
| v2 + editor self-reflection | 97% | 100% | 100% |

v1 read a ₹2.75 lakh overdue balance to the customer's wife, invented bank account numbers and payment plans, and
answered "what if I don't pay?" with a list of penalties. Its median reply was 83 words; v2's is 19.

## What I'd take into Peakflo
1. **Put numbers in tools, not prompts.** Grounding in pre-computed facts did most of the work (13% → 93%).
2. **Check numbers with code, judge tone with an LLM.** My LLM editor fixed a real problem, but 5 of its 9 flags
   were false alarms on correct amounts. Each false alarm adds a full LLM call of latency on a live phone call.
3. **Rule precedence matters.** The one remaining failure: "we already paid some, what's left?" gets a request for
   a payment reference instead of the balance. Answer first, then ask.
4. **Distrust your own metrics.** My checker was wrong twice (a curly apostrophe; "we are *not* taking legal
   action" counted as a threat). I fixed both with tests after reading every failure by hand.

## With real Peakflo data, next
- Replay real (anonymised) call transcripts as the test set, weighted by how often each situation happens.
- Add the audio path: TTS pronunciation of lakh and crore amounts and names, barge-in handling, and a latency budget
  per turn on LiveKit.
- Run each prompt version several times and on two models before shipping, and track these checks per release
  so a prompt change can't quietly break privacy or compliance.
