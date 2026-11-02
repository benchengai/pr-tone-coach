#!/usr/bin/env bash
# Check your own draft code review comment before you post it. Nothing is posted.
#
#   examples/pre-send-check.sh draft.md                  # gpt-6.1-terra, rewrite re-checked
#   examples/pre-send-check.sh draft.md --model gpt-6-luna
#   examples/pre-send-check.sh draft.md --rules          # offline keyword baseline
#
# Exit status: 0 low risk, 3 medium or high risk, 1 the check failed.
# Posting stays your decision; when you are happy with the text, post it yourself,
# for example with `gh pr review <PR> --comment --body-file draft.md`.
set -euo pipefail

draft="${1:?usage: pre-send-check.sh DRAFT_FILE [prtone check options]}"
shift
repo="$(cd "$(dirname "$0")/.." && pwd)"
extra=(--recheck)
for arg in "$@"; do [[ "$arg" == "--rules" ]] && extra=(); done

status=0
uv run --project "$repo" prtone check --file "$draft" ${extra[@]+"${extra[@]}"} --fail-on medium "$@" || status=$?
echo
case $status in
  0) echo "Low risk. Nothing was posted; post it yourself when ready." ;;
  3) echo "Medium or high risk: see the flagged phrases and any rewrite above. Nothing was posted." ;;
  *) echo "The check failed (status $status). Nothing was posted." ;;
esac
exit "$status"
