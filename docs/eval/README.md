# PR Tone Coach evaluation report

What this measures: how well the checker labels draft code review comments,
whether the phrases it quotes are real and are the right ones, whether its
rewrites keep the technical content, and what each model costs. Every number
comes from `prtone bench` runs; the per-run JSON files (with API request ids)
are in `runs/` (not committed) and the tables are generated from them.

**Headline.** On 45 synthetic comments, `gpt-6-luna`, `gpt-6.1-terra` and
`gpt-6.1-sol` agree with the gold target in macro-F1 0.91–0.98 and with the
gold risk in 0.97–0.98 (keyword baseline 0.71 and 0.69); every quote they
returned was in the draft; 99–100% of rewrites kept every identifier, code
span, number and path, and the judge passed 93–96% on all four rubric
criteria. On 100 held-out human-labelled Gerrit comments, "medium or high
risk" matches the human toxic label with F1 0.83–0.87 (baseline 0.72), while
"high" alone catches only 14–19% of toxic comments: most toxic comments in
the sample call the code ugly or say it sucks, which this tool rates medium. `gpt-6-luna` costs $0.00013–0.00017
per comment, a sixth of `gpt-6.1-terra` and a tenth of `gpt-6.1-sol`, with no
loss on these tests. The synthetic labels come from the prompt's author, so
read the synthetic numbers as a smoke test.

## Method

### What is measured

| Question | Metric | How |
|---|---|---|
| Does the checker name the right target? | Target macro-F1 (4 classes: code, person, tool or process, none) | Against gold labels; macro-F1 averages per-class F1 over the classes present |
| Does it rate the risk right? | Risk macro-F1 (low, medium, high); exact agreement; flag F1 (medium or high vs low); recall of gold "high" | Against gold labels |
| Are the quoted phrases real? | Quotes verified | Share of returned quotes found verbatim in the draft (exact up to case, whitespace and typographic quotes; [evidence.py](../../prtone/evidence.py)). Unverified quotes are dropped before display |
| Are they the right phrases? | Gold phrases hit; phrase overlap F1 | Share of gold phrases that a verified phrase overlaps; character-level precision, recall and F1 against gold phrase spans |
| Does the rewrite keep the technical content? | Tokens all kept; tokens kept | Deterministic: every identifier, code span, number, file path, URL and issue reference of the draft must appear in the rewrite ([tokens.py](../../prtone/tokens.py)). Numbers that only occur inside a flagged phrase ("for the third time") are exempt |
| ...including what tokens cannot see? | Judge: technical points kept, no added claims, request strength kept, respectful, all four | An LLM judge with a fixed rubric ([judge.py](../../prtone/judge.py)) lists dropped points, invented claims, softened requests and remaining disrespect before answering; a criterion passes only if its list is empty. Spot-checked by hand (below) |
| Is the rewrite actually safer? | Risk after rewrite | The same model checks its own rewrite; share rated low and high |
| What does it cost? | Cost per comment, latency mean and p90 | Token usage from the API response times published prices ([pricing.py](../../prtone/pricing.py)); wall-clock time per call |

Every model runs every comment three times; tables show the mean across runs
and the range in brackets. Each (model, run, comment) result is cached as a
JSON file with the raw model output and the API request id, and the
deterministic checks are re-run on the raw output whenever results are scored,
so a change to a checker never leaves stale numbers.

### Setup

| | |
|---|---|
| Synthetic test set | 45 comments written and labelled for this project ([data/gold](../../data/gold/README.md)): target code 22, person 11, tool or process 7, none 5; risk low 17, medium 18, high 10; 4 marked borderline. Written together with the 30-comment development set before any model saw either; prompts were written on the development set only and frozen before the first test run (prompt hashes `check f02c22fccaeb`, `judge fb273c3e8abe`, recorded in each `results.json`) |
| External held-out sample | 100 Gerrit code review comments from ToxiSpanSE (Sarker et al. 2023): 50 labelled toxic by the dataset's two raters, 50 not, drawn with a fixed seed from the 12,005 unique comments of 20 to 600 characters (18.7% toxic). Never used for prompt work; looked at only for the error analysis below. Rewrites were not re-checked or judged here, to save budget |
| Models | `gpt-6-luna`, `gpt-6.1-terra`, `gpt-6.1-sol` through the OpenAI Responses API with strict JSON-schema output and default reasoning settings; the keyword baseline ([rules.py](../../prtone/rules.py)) |
| Runs | 3 per model and set; the keyword baseline once (it is deterministic) |
| Judge | `gpt-6.1-sol`, rubric version 2, on every rewrite of run 1 (85 rewrites); spot-checked by hand ([judge-spot-check.md](judge-spot-check.md)) |
| Cost | Published standard prices as of 2026-11-02 ([pricing.py](../../prtone/pricing.py)); about 1,160 input tokens per check, 98–99% of them served from OpenAI's prompt cache (the system prompt is identical for every call) |
| Machine | Calls made from a laptop in parallel (6 at a time); latency is wall-clock time per call |

Commands:

```bash
uv run prtone bench data/gold/synthetic_test.jsonl --runs 3 --judge openai:gpt-6.1-sol \
  -m rules openai:gpt-6-luna openai:gpt-6.1-terra openai:gpt-6.1-sol \
  -o runs/test/synthetic --report docs/eval/synthetic-test.md
uv run python -I scripts/fetch_data.py && uv run python -I scripts/make_toxispanse_sample.py
uv run prtone bench data/external/toxispanse_test.jsonl --runs 3 --judge none --no-recheck \
  -m rules openai:gpt-6-luna openai:gpt-6.1-terra openai:gpt-6.1-sol \
  -o runs/test/toxispanse --report docs/eval/toxispanse-test.md
uv run python scripts/report_details.py > docs/eval/details.md
```

Full generated tables: [synthetic-test.md](synthetic-test.md),
[toxispanse-test.md](toxispanse-test.md), [details.md](details.md)
(confusion matrices, per-class F1, items wrong in most runs, cost per step).

## Results

### Synthetic test set (45 comments)

| Model | Target macro-F1 | Risk macro-F1 | Flag F1 (medium+) | High recall | Quotes verified | Gold phrases hit | Phrase overlap F1 | Cost per comment (USD) | Latency mean / p90 (s) | Failed runs |
|---|---|---|---|---|---|---|---|---|---|---|
| keyword baseline | 0.71 | 0.69 | 0.79 | 0.50 | 1.00 | 0.60 | 0.30 | 0 | 0.0 | 0 |
| `gpt-6-luna` | 0.96 (0.93–0.98) | 0.97 (0.96–0.97) | 0.99 (0.98–1.00) | 1.00 | 1.00 | 0.98 (0.97–1.00) | 0.92 (0.91–0.93) | 0.00013 | 3.2 / 5.0 | 0 of 3 |
| `gpt-6.1-terra` | 0.91 (0.90–0.93) | 0.98 (0.97–1.00) | 1.00 | 1.00 | 1.00 | 0.97 | 0.92 (0.90–0.92) | 0.00082 | 3.1 / 4.4 | 0 of 3 |
| `gpt-6.1-sol` | 0.98 (0.98–1.00) | 0.97 (0.95–0.97) | 1.00 | 1.00 | 1.00 | 0.98 (0.97–1.00) | 0.91 (0.91–0.92) | 0.00109 | 3.0 / 5.0 | 0 of 3 |

Rewrites (about 28 per run, one for each comment rated medium or high).
Tokens and re-check: all three runs. Judge: run 1 only (85 rewrites).

| Model | Tokens all kept | Re-checked: low | Re-checked: high | Judge: points kept | No added claims | Requests not softened | Respectful | All four |
|---|---|---|---|---|---|---|---|---|
| `gpt-6-luna` | 0.99 (0.96–1.00) | 0.91 (0.89–0.93) | 0.00 | 0.97 | 0.97 | 1.00 | 1.00 | 0.93 |
| `gpt-6.1-terra` | 1.00 | 0.89 | 0.00 | 0.96 | 1.00 | 1.00 | 0.96 | 0.93 |
| `gpt-6.1-sol` | 1.00 | 0.94 (0.93–0.96) | 0.00 | 1.00 | 0.96 | 1.00 | 1.00 | 0.96 |

### External held-out sample (100 human-labelled Gerrit comments)

"Flag" means the checker rated the comment medium or high. Precision is on
the balanced sample; the re-weighted column estimates it at the population's
18.7% toxic rate. "Span hit" is the share of the human-marked toxic spans that
a verified quote overlaps.

| Model | Flag: P | Flag: R | Flag: F1 | Flag P at 18.7% | High: P | High: R | Quotes verified | Span hit | Rewrites keeping all tokens | Cost per comment (USD) | Latency mean / p90 (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| keyword baseline | 0.77 | 0.68 | 0.72 | 0.44 | 0.82 | 0.28 | 1.00 | 0.59 | – | 0 | 0.0 |
| `gpt-6-luna` | 0.85 (0.83–0.87) | 0.89 (0.88–0.90) | 0.87 (0.85–0.88) | 0.56 | 0.90 | 0.19 | 0.99 (2 of 249 failed) | 0.86 (0.82–0.89) | 157 of 157 | 0.00017 | 4.0 / 6.5 |
| `gpt-6.1-terra` | 0.90 (0.88–0.91) | 0.77 (0.76–0.78) | 0.83 (0.82–0.84) | 0.67 | 0.87 | 0.14 | 1.00 | 0.74 (0.73–0.75) | 128 of 128 | 0.00097 | 3.4 / 5.4 |
| `gpt-6.1-sol` | 0.85 (0.84–0.86) | 0.85 (0.84–0.86) | 0.85 (0.84–0.86) | 0.56 | 0.88 | 0.15 | 1.00 | 0.89 | 151 of 151 | 0.00166 | 4.3 / 7.4 |

## Findings

1. **The synthetic set does not separate the models.** All three agree with
   the gold labels almost everywhere and none failed a run. The errors left
   cluster on four items, two of them marked borderline before any run (t13,
   t18). The clearest disagreement is t08, "You never write tests for edge
   cases": the gold says medium (a habit, no insult), `gpt-6.1-sol` said high
   in 3 of 3 runs and `gpt-6.1-terra` in 2 of 3. The line between criticising
   a habit and contempt is where the guidelines are least crisp. The keyword
   baseline is far behind (risk macro-F1 0.69, high recall 0.50): it misses
   person-directed attacks phrased without insult words ("Are you trying to
   get us hacked?", "Whoever wrote this should be banned...").
2. **Against human toxicity labels, "medium or high" agrees well and "high"
   does not.** ToxiCR's definition is expansive: it counts mild words about
   code as toxic. Of the 35 toxic comments `gpt-6.1-sol` rated medium in most
   runs, 23 call the code ugly, say it sucks or say yuck, 4 are swearing and 3
   call something stupid. This tool's guideline rates a vague negative
   judgement of the code as medium and keeps high for insults, contempt or
   mockery; whether "this sucks" is contempt for the work (high) or a vague
   negative (medium) is a call the guideline leaves open, and the models chose
   medium. The models also labelled 77–80% of the toxic comments as aimed at
   the code and only 6–9% at the person. That split echoes Gachechiladze et
   al.'s observation that most anger in developer comments is aimed at
   objects, but here it is the models' labelling, not a human one.
3. **Most disagreements are construct differences, not misses.** Reading the
   comments where most of the nine model runs disagreed with the human label:
   - 8 toxic comments rated low: six are exclamations or self-deprecation by
     the commenter (swearing at their own mistake, "brain fart"), one uses
     "nuke" as Gerrit slang for deleting code, one calls the commenter's own
     style nit "stupid". By this tool's guideline, unaimed profanity should
     be medium, so here the models are more lenient than the guideline.
   - 7 non-toxic comments flagged: five open with a curt verdict that the
     code is useless or changes nothing, which is a pushback cue by this
     tool's definition and outside ToxiCR's; one calls code by an ableist slur
     the dataset labels non-toxic; one is the commenter calling their own
     change stupid, which the models rated high because the target scheme has
     no "self" option. That last one is a real gap.
4. **In a realistic stream, about every second flag would not be "toxic".**
   Re-weighted to the 18.7% toxic rate of the population, flag precision is
   0.56 for `gpt-6-luna` and `gpt-6.1-sol` and 0.67 for `gpt-6.1-terra`.
   Finding 3 suggests many of those extra flags are curt pushback the tool is
   meant to catch, but that was judged on seven comments, not measured.
5. **Quotes are real and mostly the right ones.** 638 of 640 quotes on real
   comments verified; the two failures are `gpt-6-luna` dropping Markdown
   emphasis (`*really* ugly` quoted as "really ugly"), which the strict check
   rejects. The verifier was not loosened after seeing this. Human toxic spans
   are hit 86–89% of the time by `gpt-6-luna` and `gpt-6.1-sol` and 74% by
   `gpt-6.1-terra`, which quotes fewer phrases (169 against 222 and 249 over
   three runs).
6. **Rewrites keep the technical content; the failures are specific.** On
   real comments every one of 436 rewrites kept every technical token; on the
   synthetic set one of 253 dropped one (`ORMs`, together with the only
   reason the draft gave). The judge's failures, all confirmed by hand
   ([spot check](judge-spot-check.md)): asked to rewrite "Whoever wrote this
   should be banned from touching the auth code", `gpt-6-luna` and
   `gpt-6.1-sol` invented a merge block the draft never made, and
   `gpt-6.1-terra` kept the attack ("further auth code changes from this
   author must be blocked"). The judge itself agreed with the hand check on
   18 of 20 verdicts, erring once in each direction.
7. **Rewrites are safer but not always low risk, and that is intended.**
   89–94% of rewrites re-check as low and none as high. Of the 22 that
   re-check as medium, 16 contain a `[reason]` placeholder the author still
   has to fill in, and the remaining cues are mostly *blocking without
   reason* (10), *impatience* (6) and *vague negative* (5): a block stays
   pushback until the author says why.
8. **The cheapest model is enough here.** Prompt caching serves 98–99% of
   the ~1,160 input tokens per check, so cost is mostly output. `gpt-6-luna`
   writes the most output (224 tokens, 170 of them reasoning, against 93 for
   `gpt-6.1-sol`) at a twentieth of the output price: $0.00013–0.00017 per
   comment against $0.0008–0.0010 (`gpt-6.1-terra`) and $0.0011–0.0017
   (`gpt-6.1-sol`). It had the best flag F1 on human labels (0.87) with the
   highest false-positive rate (0.16 against 0.09 for `gpt-6.1-terra`), and
   matched the others on rewrites. Mean latency is 3–4 s for all three. The
   CLI default was switched from `gpt-6.1-terra` to `gpt-6-luna` after these
   runs; no measured number depends on the default.

## How the prompts were developed

On the 30-comment development set only, in three rounds
(`runs/dev/v1`–`v3`, $0.18 in total):

1. First prompt and keyword baseline. `gpt-6-luna` already scored target 1.00
   and risk 0.93; `gpt-6.1-terra` under-called "high" on contemptuous remarks
   about competence ("Did you even read the ticket?").
2. The risk definitions were rewritten to match the labelling guidelines on
   that point; dev risk macro-F1 rose to 1.00 (`gpt-6-luna`) and 0.97
   (`gpt-6.1-terra`). One development label (d02) was marked borderline; no
   label was changed.
3. The judge rubric was revised after a hand check of its dev verdicts showed
   it counting the reviewer's seniority, "as I said before" and injected
   instructions as technical points, and counting "please give a reason" as
   an invented claim. Two of the eight dev failures were real (a dropped
   `CacheManager`, a dropped "Jenkins") and the revised rubric still caught
   them.

Two deterministic fixes came from development as well: duplicate quotes are
merged, and numbers inside a flagged phrase ("for the third time") are no
longer required in the rewrite.

## Limitations of this evaluation

- The synthetic comments and their labels come from one author, who also
  wrote the prompts and the judge rubric. Shared conventions inflate the
  synthetic scores; the external sample exists to counter that, but it
  measures toxicity, a narrower construct.
- Several cue words used as examples in the prompt ("garbage", "did you
  even") also occur in synthetic test comments.
- The judge is `gpt-6.1-sol`, which also wrote a third of the judged
  rewrites; self-preference cannot be ruled out. 20 of 85 verdicts were read
  by a person, the same assistant that wrote the rubric.
- External rewrites were not judged or re-checked, so rewrite quality on real
  comments is measured only by the token check.
- 45 and 100 comments, 3 runs: confidence intervals would be wide (one
  synthetic item is 2.2 points of accuracy). Ranges show run-to-run spread
  only, not sampling error.
- Latency was measured from one laptop on one afternoon, with up to six
  calls in flight; prices are list prices on 2026-11-02.

