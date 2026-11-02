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

<!-- RESULTS -->

## The problem

<!-- PROBLEM -->

## What it does

```
$ uv run prtone check "Did you even run this? \`getUser()\` returns null on 404, which is obviously wrong."
```

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
uv run prtone check --file draft.md --model gpt-6-luna --recheck
uv run prtone check --file draft.md --rules        # offline keyword baseline
uv run prtone check --file draft.md --json         # full result, for tools
examples/pre-send-check.sh draft.md                # exit 3 on medium or high risk
```

The default model is `gpt-6.1-terra`; `--model` takes `gpt-6-luna`,
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
npx serve out      # or: npm run dev
```

The demo needs no API key and loads instantly: it shows stored outputs of real
pipeline runs (with their API request ids) on the synthetic test comments, the
highlighted phrases, target and risk badges, a side-by-side diff of the
rewrite, the token check, the re-check and the judge verdict, and Research
basis and Limitations panels. It is a static export (`output: 'export'`) that
can be deployed to Vercel as is; it has not been deployed.

<!-- REST -->
