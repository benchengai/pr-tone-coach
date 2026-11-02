# Judge spot check (synthetic test set, run 1)

The rewrite judge (`gpt-6.1-sol`, rubric version 2, [judge.py](../../prtone/judge.py))
was checked by hand on 20 of its 85 verdicts: a seeded random sample of 15
(`scripts/spot_check.py runs/test/synthetic --n 15 --seed 7`; all 15 happened
to be passes) plus every verdict that failed a rewrite (5). The reviewer
(Claude Code, the same assistant that wrote the rubric) read the draft, the
rewrite and the judge's lists and recorded agreement before looking at the
test-set judge scores.

**Agreement: 18 of 20 (14 of 15 passes, 4 of 5 failures).**

## Disagreements

| Item | Model | Judge | Reviewer | Why |
|---|---|---|---|---|
| t04 | `gpt-6-luna` | pass | fail (technical points) | The draft ("do you even know what a mutex is? `counter += 1` from 8 goroutines is a data race") points at a mutex as the fix; the rewrite asks "what synchronization protects this access?" and drops the mutex. Borderline: the draft only implies it |
| t29 | `gpt-6.1-terra` | fail (technical points) | pass | The judge counted "everything about `normalize_address()` is wrong" as a dropped point. It is a vague negative judgement, which the rubric says is tone, not a technical point; the rewrite keeps the function and asks for the issue with a placeholder |

So the judge errs in both directions, about once in ten on this sample.

## Failures the reviewer agrees with

| Item | Model | Finding |
|---|---|---|
| t22 | `gpt-6-luna`, `gpt-6.1-sol` | Both turned "Whoever wrote this should be banned from touching the auth code" into a merge block ("must be fixed before the change can be merged"). The draft made no merge-blocking request; the rewrite invented one |
| t22 | `gpt-6.1-terra` | Rewrote the same line as "Further auth code changes from this author must be blocked [reason]": still aimed at the person |
| t32 | `gpt-6-luna` | Dropped "we don't use ORMs", the only reason given, keeping just the request and a placeholder (the token check also flagged `ORMs`) |

## Passes worth noting

- t15 (`gpt-6.1-terra`): "-2. Rework it." became "-2. Rework it. [reason]".
  The rubric passes it (nothing dropped, invented or disrespectful), but the
  rewrite barely changes the comment. The rubric checks faithfulness, not
  whether the rewrite reads better; the re-check measures that.
- t16 (`gpt-6.1-sol`): "Are you trying to get us hacked?" became "which
  exposes us to CSRF attacks". Counted as implied by the draft, not invented.
