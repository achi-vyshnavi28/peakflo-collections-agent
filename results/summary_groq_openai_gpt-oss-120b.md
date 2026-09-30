Model: `groq/openai/gpt-oss-120b` · 30 scenarios · temperature 0

| Config | All checks pass | Handles the situation | No invented amount | No threat | Voice ready | Rewrites |
|---|---|---|---|---|---|---|
| v1 | 13% | 77% | 93% | 97% | 17% | 0 |
| v2 | 93% | 97% | 100% | 100% | 97% | 0 |
| v2_reflect | 97% | 97% | 100% | 100% | 100% | 9 |

Failures by situation (scenarios failing any check):

| Situation | v1 | v2 | v2_reflect |
|---|---|---|---|
| angry | 2/2 | 0/2 | 0/2 |
| ask_amount | 4/4 | 1/4 | 1/4 |
| ask_due_date | 2/2 | 0/2 | 0/2 |
| callback | 1/2 | 0/2 | 0/2 |
| dispute | 2/2 | 0/2 | 0/2 |
| hardship | 2/2 | 0/2 | 0/2 |
| hinglish_hardship | 1/1 | 1/1 | 0/1 |
| invoice_copy | 1/1 | 0/1 | 0/1 |
| paid | 2/2 | 0/2 | 0/2 |
| partial | 2/2 | 0/2 | 0/2 |
| payment_link | 2/2 | 0/2 | 0/2 |
| stop | 0/2 | 0/2 | 0/2 |
| threat_bait | 2/2 | 0/2 | 0/2 |
| waiver | 1/2 | 0/2 | 0/2 |
| wrong_person | 2/2 | 0/2 | 0/2 |
