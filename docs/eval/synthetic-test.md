### `synthetic_test.jsonl`: 45 comments, 3 runs per model

Mean across runs, range in brackets. The keyword baseline is deterministic and runs once.

| Model | Target macro-F1 | Risk macro-F1 | Risk exact | Flag F1 (medium+) | High recall | Quotes verified | Phrase overlap F1 | Gold phrases hit | Cost per comment (USD) | Latency mean / p90 (s) | Failed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `rules` | 0.71 | 0.69 | 0.71 | 0.79 | 0.50 | 1.00 | 0.30 | 0.60 | 0.00000 | 0.0 / 0.0 | 0 |
| `openai:gpt-6-luna` | 0.96 (0.93–0.98) | 0.97 (0.96–0.97) | 0.97 (0.96–0.98) | 0.99 (0.98–1.00) | 1.00 | 1.00 | 0.92 (0.91–0.93) | 0.98 (0.97–1.00) | 0.00013 (0.00012–0.00013) | 3.2 (3.1–3.3) / 5.0 (4.8–5.2) | 0 |
| `openai:gpt-6.1-terra` | 0.91 (0.90–0.93) | 0.98 (0.97–1.00) | 0.99 (0.98–1.00) | 1.00 | 1.00 | 1.00 | 0.92 (0.90–0.92) | 0.97 | 0.00082 (0.00077–0.00087) | 3.1 (3.0–3.3) / 4.4 (4.3–4.4) | 0 |
| `openai:gpt-6.1-sol` | 0.98 (0.98–1.00) | 0.97 (0.95–0.97) | 0.97 (0.96–0.98) | 1.00 | 1.00 | 1.00 | 0.91 (0.91–0.92) | 0.98 (0.97–1.00) | 0.00109 (0.00099–0.00118) | 3.0 (2.8–3.1) / 5.0 (4.5–5.4) | 0 |

Rewrites. Tokens: share of rewrites that keep every identifier, code span, number, path and URL of the draft (deterministic). After: the same model re-checks its rewrite. Judge: `openai:gpt-6.1-sol` with a fixed rubric, on the rewrites of the first 1 run(s).

| Model | Rewrites per run | Tokens all kept | Tokens kept | After: low | After: high | Judge: points kept | No added claims | Request strength kept | Respectful | All four |
|---|---|---|---|---|---|---|---|---|---|---|
| `openai:gpt-6-luna` | 28.3 (28.0–29.0) | 0.99 (0.96–1.00) | 0.99 (0.98–1.00) | 0.91 (0.89–0.93) | 0.00 | 0.97 | 0.97 | 1.00 | 1.00 | 0.93 |
| `openai:gpt-6.1-terra` | 28.0 | 1.00 | 1.00 | 0.89 | 0.00 | 0.96 | 1.00 | 1.00 | 0.96 | 0.93 |
| `openai:gpt-6.1-sol` | 28.0 | 1.00 | 1.00 | 0.94 (0.93–0.96) | 0.00 | 1.00 | 0.96 | 1.00 | 1.00 | 0.96 |
