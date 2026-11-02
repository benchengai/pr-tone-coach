# PR Tone Coach

Check your own code review comment before you post it. For a draft comment,
PR Tone Coach reports:

- **who the criticism targets**: the code, the person, a tool or process, or
  nothing (no criticism);
- **the risk that it reads as destructive criticism or pushback** (low,
  medium, high), with the exact phrases that drive it, each checked to be in
  the draft;
- **a rewrite that keeps every technical point**, with a deterministic check
  that every identifier, code span, number, file path, URL and issue
  reference of the draft survives.

It labels comment text, never people: no per-person scores, no history of who
wrote what, and no guesses about how the writer feels.

Portfolio app 2 of 5 built from the systematic mapping study *Emotions in
Software Engineering* (57 studies).

## The problem

A review comment is written once and read by someone whose work it judges.
Code review research describes what phrasing costs beyond the technical point:
Egelman et al. (2020) studied pushback, the perception of unnecessary
interpersonal conflict while a reviewer blocks a change, and the negative
feelings that come with it; a vignette survey of 93 practitioners found that
destructive criticism, negative feedback that is both nonspecific and
inconsiderate, affects inclusion (Gunawardena et al. 2022); uncivil and toxic
review comments have been characterised and detected automatically (Ferreira
et al. 2021; Sarker et al. 2023).

Most of that work examines comments after they were posted (ToxiShield,
Anindya et al. 2026, which filters toxic text in real time, is a recent
exception). In the mapping study behind this portfolio, studies that mine
review comments are filed under Maintenance, and the cell **Communication &
Collaboration × Design/Implementation has 0 studies**. PR Tone Coach works at
that point instead: the author of the comment checks it while writing it, when
it can still be changed and before anyone else has read it.

## What it does

```
$ uv run prtone check --recheck "Did you even run this? \`getUser()\` returns null on 404, which is obviously wrong."
Risk:   HIGH  (reads as destructive criticism or pushback)
Target: the person

Draft:
  [[Did you even run this?]] `getUser()` returns null on 404, which is [[obviously]] [[wrong]].

Phrases:
  - "Did you even run this?"  (person directed)
  - "Did you even"  (condescending)
  - "obviously"  (condescending)
  - "wrong"  (vague negative)

Suggested rewrite:
  Please confirm this was run. `getUser()` returns null on 404, which is [reason this is incorrect].

Changes:
  [-Did you even run this?-] {+Please confirm this was run.+} `getUser()` returns null on 404, which is [-obviously wrong.-] {+[reason this is incorrect].+}

Technical tokens: 2 of 2 kept (all kept)
Rewrite re-checked: risk low

gpt-6-luna: 6.56 s, $0.0003. Labels describe the text, not its writer.
```

(A real run, copied as printed. `[[...]]` marks the quoted phrases; square
brackets in the rewrite are placeholders for the author to fill in.)

1. One LLM call with a strict JSON schema returns the phrases that carry the
   risk (each with a cue type such as *person-directed*, *condescending* or
   *blocking without reason*), the target, the risk level and, for medium or
   high risk, a rewrite ([prtone/check.py](prtone/check.py)).
2. Code then checks what the model said ([prtone/evidence.py](prtone/evidence.py),
   [prtone/tokens.py](prtone/tokens.py)): every quoted phrase must be in the
   draft (quotes that are not are dropped and reported); every technical token
   of the draft must be in the rewrite (missing ones are listed); risk above
   low with no supporting phrase is flagged.
3. Optionally (`--recheck`) the rewrite is checked again with the same model.

`--rules` runs a keyword baseline instead: no API key, no rewrite, the same
output shape ([prtone/rules.py](prtone/rules.py)).

The cue types are text features, not emotions: "condescending" describes a
phrase like "obviously", not the state of the person who typed it.

## Quick start

Requires [uv](https://docs.astral.sh/uv/) and, for the LLM checker, an OpenAI
API key in `.env` at the repository root (git-ignored), or in a file named by
`PRTONE_ENV_FILE`:

```
OPENAI_API_KEY=...
```

```bash
uv sync
uv run pytest
uv run prtone check "This is garbage. \`retry()\` never backs off."
uv run prtone check --file draft.md --model gpt-6.1-sol --recheck
uv run prtone check --file draft.md --rules        # offline keyword baseline
uv run prtone check --file draft.md --json         # full result, for tools
examples/pre-send-check.sh draft.md                # exit 3 on medium or high risk
```

The default model is `gpt-6-luna`, the cheapest of the three, which matched
the larger models in the evaluation; `--model` takes `gpt-6-luna`,
`gpt-6.1-terra` or `gpt-6.1-sol` (or `openai:<model>`).

Before posting, two ways to wire it in, neither of which posts anything:

- [examples/pre-send-check.sh](examples/pre-send-check.sh): run it on a local
  draft file; you post the comment yourself afterwards (for example with
  `gh pr review <PR> --comment --body-file draft.md`).
- [examples/github-actions/check-my-draft.yml](examples/github-actions/check-my-draft.yml):
  a manually started (`workflow_dispatch`) workflow with read-only permissions
  that checks a draft you paste in and writes the result to the job summary.
  It never runs on pull request or comment events, so it never reads anyone
  else's comments.

### Web demo

```bash
cd web
npm install
npm run build      # static export in web/out/
npm start          # serves web/out on http://localhost:4317 (or: npm run dev)
```

The demo needs no API key and loads instantly: it shows stored outputs of real
pipeline runs (with their API request ids) on the synthetic test comments, the
highlighted phrases, target and risk badges, a side-by-side diff of the
rewrite, the token check, the re-check and the judge verdict, and Research
basis and Limitations panels. It is a static export (`output: 'export'`) that
can be deployed to Vercel as is; it has not been deployed.

## Results

Full report with method, tables, error analysis and limitations:
[docs/eval](docs/eval/README.md). Three runs per model; mean shown, range in
the report. Total API spend for development and evaluation: **$1.60**.

| | keyword baseline | `gpt-6-luna` | `gpt-6.1-terra` | `gpt-6.1-sol` |
|---|---|---|---|---|
| **Synthetic test set (45 comments, labels by the prompt's author)** | | | | |
| Target macro-F1 | 0.71 | 0.96 | 0.91 | 0.98 |
| Risk macro-F1 | 0.69 | 0.97 | 0.98 | 0.97 |
| Quotes found verbatim in the draft | 1.00 | 1.00 | 1.00 | 1.00 |
| Gold phrases hit by a quote | 0.60 | 0.98 | 0.97 | 0.98 |
| Rewrites keeping every technical token | – | 0.99 | 1.00 | 1.00 |
| Rewrites passing all four judge criteria | – | 0.93 | 0.93 | 0.96 |
| Rewrites re-checked as low risk | – | 0.91 | 0.89 | 0.94 |
| **Held-out human-labelled sample (100 Gerrit comments, ToxiSpanSE)** | | | | |
| Medium or high vs toxic label: F1 | 0.72 | 0.87 | 0.83 | 0.85 |
| High vs toxic label: recall | 0.28 | 0.19 | 0.14 | 0.15 |
| Human toxic spans hit by a quote | 0.59 | 0.86 | 0.74 | 0.89 |
| **Cost and speed** | | | | |
| Cost per comment (USD) | 0 | 0.00013–0.00017 | 0.0008–0.0010 | 0.0011–0.0017 |
| Mean latency (s) | 0 | 3.2–4.0 | 3.1–3.4 | 3.0–4.3 |

What this shows:

- On the synthetic set the three models are close to the gold labels and to
  each other; the keyword baseline is not. The synthetic labels share the
  prompt's conventions, so this mostly shows the models follow the
  guidelines.
- Against independent human labels, "medium or high risk" lines up with
  toxicity (F1 up to 0.87), but "high" does not: the human scheme counts mild
  words about code ("ugly", "sucks") as toxic, while this tool rates them as
  vague negatives (medium) and keeps "high" for insults, contempt and
  mockery. Most other disagreements were construct differences too (curt
  "this is useless" verdicts flagged as pushback; swearing at one's own
  mistake rated low), plus one real gap: the target scheme has no "self".
- Every quote but two of 640 on real comments was verbatim, and every one of
  436 rewrites of real comments kept every technical token.
- `gpt-6-luna` matched the larger models at a sixth to a tenth of the cost,
  so it is the default.

## Privacy and scope

- **A writing aid on a text artefact, used by its author.** You run it on your
  own draft before posting. It is not built to read other people's comments,
  and the examples only ever check a draft you hand them.
- **Labels describe text, not people.** No per-person score, no profile, no
  history: each check is independent and nothing is stored unless you save
  the output yourself. The cue types ("condescending", "dismissive") name
  features of phrases. The tool never infers the writer's emotions: the EU AI
  Act, Art. 5(1)(f), prohibits AI emotion inference about people at work, and
  emotional states cannot be reliably inferred even from facial movements
  (Barrett et al. 2019); the tool applies the same caution to text.
- **Where the draft goes.** The LLM checker sends the draft to the OpenAI API
  (no other data). Do not paste secrets. `--rules` runs offline.
- **Synthetic demo data.** The demo and the synthetic gold sets contain only
  comments written for this project.

## Limitations

- **The synthetic set is easy and one-sided.** Its 75 comments and labels were
  written by one author, the same one who wrote the prompt (Claude Code, an AI
  coding assistant, for this project), and no second person labelled them.
  Near-perfect agreement on it shows the models follow the guidelines, not
  that the guidelines match how developers read comments.
- **The human labels measure a different construct.** ToxiSpanSE labels
  toxicity (insults, threats, swearing and more), not pushback or destructive
  criticism. A curt but civil block is not toxic and is still pushback;
  calling code "ugly" is toxic there and only medium risk here. Agreement
  with it checks the scale only partly.
- **The text is not the whole story.** Pushback and destructive criticism are
  perceptions of the recipient (Egelman et al. 2020; Gunawardena et al.
  2022). The checker sees only the comment: not the relationship, the history
  of the change or the team's norms.
- **The judge is a model too.** The rewrite judge is `gpt-6.1-sol`, from the
  same provider as every checked model and the same model as one of them. A
  hand spot check agreed with 18 of 20 verdicts; the other 65 were not read
  by a person. Risk after rewrite is rated by the model that wrote the
  rewrite.
- **The token check is necessary, not sufficient.** It does not see plain
  names such as "Jenkins" or numbers written as words, and it treats code in
  a rewrite without backticks as kept.
- **Scope.** Mostly English (one German test comment). OpenAI models only;
  the code keeps the call behind one function so another provider is a small
  change, but none was tested here. No user study: there is no evidence yet
  that the rewrites change how comments are received.
- **Small numbers.** 45 synthetic and 100 external comments, 3 runs each. One
  item moves a per-class F1 by several points.

## Research basis

The labels and cue types are grounded in, not validated by, the work below.
"Included study" means one of the 57 studies in the mapping study.

| Source | What it gives this tool |
|---|---|
| Egelman et al. 2020 (included study) | **Pushback**: the perception of unnecessary interpersonal conflict while a reviewer blocks a change. Detected there from review logs (rounds, reviewing and shepherding time), not text. Here: the risk framing and the *blocking without reason* cue |
| Gunawardena et al. 2022 | **Destructive criticism**: negative feedback that is both nonspecific and inconsiderate (harsh or sarcastic tone, threats, blaming the person). Here: *vague negative*, *mocking or sarcasm*, *aimed at the person*, and the rule that blunt but specific feedback is low risk |
| Ferreira et al. 2021 | **Incivility** in Linux kernel review emails, coded as uncivil features: bitter frustration, impatience, irony, mocking, name calling, threat, vulgarity. Here: *impatience*, *mocking or sarcasm*, *insult*, *threat*, *profanity* |
| Sarker et al. 2023 (ToxiCR); Sarker et al. 2023 (ToxiSpanSE) | **Toxicity** in Gerrit review comments (insults, threats, personal attacks, swearing, and more), with the toxic words marked. Here: the held-out human-labelled test sample and its spans |
| Gachechiladze et al. 2017 (included study) | **Direction** of anger in Apache Jira comments: at oneself, others or objects; most was aimed at objects such as tools or code. Here: the *target* label |
| Rahman et al. 2024; Anindya et al. 2026 (ToxiShield) | The closest prior tools: civil rewrites of uncivil review comments, and real-time toxicity filtering with rewrites. This tool adds the target, pushback beyond toxicity, quotes checked against the draft, and a deterministic check that the rewrite keeps every technical token |
| Barrett et al. 2019; EU AI Act 2024, Art. 5(1)(f) | Why the tool reports **cues in text, not emotions**, and why it is a writing aid for the author rather than a monitor of anyone |

The *dismissive*, *absolute language*, *condescending* and *authority appeal*
cues are this project's own additions; they sit close to the arrogance and
entitlement that Miller et al. (2022) found in toxic open source discussions.

### References

All entries were checked against the publisher's DOI metadata (Crossref) or
the mapping study's bibliography.

- Anindya, M. A. A., Biswas, S., Iqbal, A., Sarker, J., Bosu, A. (2026). ToxiShield: Promoting Inclusive Developer Communication through Real-Time Toxicity Filtering. *Proc. ACM Softw. Eng.* 3(FSE), 2767–2789. https://doi.org/10.1145/3808130
- Barrett, L. F., Adolphs, R., Marsella, S., Martinez, A. M., Pollak, S. D. (2019). Emotional expressions reconsidered: Challenges to inferring emotion from human facial movements. *Psychological Science in the Public Interest* 20(1), 1–68. https://doi.org/10.1177/1529100619832930
- Egelman, C. D., Murphy-Hill, E., Kammer, E., Hodges, M. M., Green, C., Jaspan, C., Lin, J. (2020). Predicting developers' negative feelings about code review. *ICSE 2020*, 174–185. https://doi.org/10.1145/3377811.3380414
- European Parliament and Council (2024). Regulation (EU) 2024/1689 (Artificial Intelligence Act). *Official Journal of the European Union*, L series. https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- Ferreira, I., Cheng, J., Adams, B. (2021). The "Shut the f\*\*k up" Phenomenon: Characterizing Incivility in Open Source Code Review Discussions. *Proc. ACM Hum.-Comput. Interact.* 5(CSCW2). https://doi.org/10.1145/3479497
- Gachechiladze, D., Lanubile, F., Novielli, N., Serebrenik, A. (2017). Anger and its direction in collaborative software development. *ICSE-NIER 2017*, 11–14.
- Gunawardena, S. D., Devine, P., Beaumont, I., Garden, L. P., Murphy-Hill, E., Blincoe, K. (2022). Destructive Criticism in Software Code Review Impacts Inclusion. *Proc. ACM Hum.-Comput. Interact.* 6(CSCW2), Article 292. https://doi.org/10.1145/3555183
- Miller, C., Cohen, S., Klug, D., Vasilescu, B., Kästner, C. (2022). "Did You Miss My Comment or What?" Understanding Toxicity in Open Source Discussions. *ICSE 2022*, 710–722. https://doi.org/10.1145/3510003.3510111
- Rahman, M. S., Codabux, Z., Roy, C. K. (2024). Do Words Have Power? Understanding and Fostering Civility in Code Review Discussion. *Proc. ACM Softw. Eng.* 1(FSE), 1632–1655. https://doi.org/10.1145/3660780
- Sarker, J., Turzo, A. K., Dong, M., Bosu, A. (2023). Automated Identification of Toxic Code Reviews Using ToxiCR. *ACM TOSEM* 32(5). https://doi.org/10.1145/3583562
- Sarker, J., Sultana, S., Wilson, S. R., Bosu, A. (2023). ToxiSpanSE: An Explainable Toxicity Detection in Code Review Comments. *ESEM 2023*, 1–12. https://doi.org/10.1109/ESEM56168.2023.10304855

## Data sources and licences

| Data | Used for | Where | Licence | Size |
|---|---|---|---|---|
| Synthetic review comments, written and labelled for this project (**synthetic**) | Prompt development (30, dev) and test (45) | [data/gold/](data/gold/README.md) | This repository | 75 comments |
| ToxiSpanSE `CR_full_span_dataset.csv` (Sarker et al. 2023): 19,651 Gerrit review comments from Android, Chromium OS, LibreOffice and OpenStack (the ToxiCR comments), 3,757 labelled toxic by two raters, with the toxic characters marked | Held-out external test: 100 comments (50 toxic, 50 not), never used for prompt work | https://raw.githubusercontent.com/WSU-SEAL/ToxiSpanSE/main/models/CR_full_span_dataset.csv | GPL-3.0. Not redistributed: [scripts/fetch_data.py](scripts/fetch_data.py) downloads it to `data/external/` (git-ignored); only row numbers and text hashes of the sample are committed ([toxispanse_test_ids.json](data/gold/toxispanse_test_ids.json)) | 4,054,763 bytes, sha256 `5d8c1df4…2be1` |

To rebuild the external sample:

```bash
uv run python -I scripts/fetch_data.py
uv run python -I scripts/make_toxispanse_sample.py
```

The sample is drawn from unique comment texts of 20 to 600 characters (12,005
texts, 18.7% toxic), 50 per class, seed 2026. Real comments from this dataset
are used only for scoring; they are not shown in the demo, and the
evaluation report quotes at most a word or two of them in its error analysis.
