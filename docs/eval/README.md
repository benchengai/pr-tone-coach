# PR Tone Coach evaluation report

<!-- SUMMARY -->

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

<!-- DETAILS -->
