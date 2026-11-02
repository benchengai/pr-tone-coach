import json
from pathlib import Path

import pytest

from prtone.bench import aggregate, load_gold, score_run
from prtone.check import CUES, RISKS, TARGETS, Verdict, assemble, reassemble
from prtone.evaluate import binary, f1_scores, phrase_overlap
from prtone.evidence import locate, verify_phrases
from prtone.report import highlight, render_text, word_diff
from prtone.rules import rule_check
from prtone.tokens import preservation, technical_tokens

ROOT = Path(__file__).resolve().parents[1]


def _values(text):
    return [(t["kind"], t["value"]) for t in technical_tokens(text)]


def test_technical_tokens_kinds():
    text = ("Did you even read src/auth/session.py? `refresh_token()` is called twice, the TTL of 3600 is "
            "wrong, see #412 and https://example.com/docs. getUserById and MAX_RETRIES too.")
    assert _values(text) == [
        ("path", "src/auth/session.py"), ("code", "refresh_token()"), ("number", "3600"), ("issue", "#412"),
        ("url", "https://example.com/docs"), ("identifier", "getUserById"), ("identifier", "MAX_RETRIES"),
    ]


def test_technical_tokens_skip_prose():
    # Acronyms, shouting, "and/or" and sentence-initial words are not technical tokens.
    assert _values("WHY is this here? LGTM and/or IMO the CI is fine. Read/write is fine.") == []
    assert ("path", "pkg/cache") in _values("read/write locks in pkg/cache are fine")


def test_fenced_code_is_one_token():
    text = "Use this instead:\n```python\nfor i, x in enumerate(xs):\n    print(i)\n```\nThanks."
    assert _values(text) == [("code", "for i, x in enumerate(xs):\n    print(i)")]
    kept = preservation(text, "Could we use:\n```python\nfor i, x in enumerate(xs):\n    print(i)\n```")
    assert kept["all_kept"]


def test_preservation_reports_missing_and_exempts_numbers_in_flagged_phrases():
    draft = "I've done this for 8 years, trust me. `LegacyAdapter` stays and the timeout is 30 s."
    flagged = [(0, draft.index(","))]
    ok = preservation(draft, "`LegacyAdapter` stays; the timeout stays at 30 s.", flagged)
    assert ok["all_kept"] and ok["exempt"] == [{"kind": "number", "value": "8"}]
    bad = preservation(draft, "LegacyAdapter stays; the timeout stays at 300 s.", flagged)
    assert [t["value"] for t in bad["missing"]] == ["30"]
    # Without the flagged span, the 8 is required too.
    assert not preservation(draft, "`LegacyAdapter` stays at 30 s.")["all_kept"]


def test_locate_exact_and_normalised():
    draft = "Did you  even read it?\nIt’s wrong."
    assert locate("Did you  even", draft) == (0, 13)
    span = locate("did you even read it", draft)
    assert draft[span[0]:span[1]] == "Did you  even read it"
    span = locate("It's wrong", draft)
    assert draft[span[0]:span[1]] == "It’s wrong"
    assert locate("you never read it", draft) is None


def test_verify_phrases_rejects_and_dedupes():
    draft = "No. No. This is garbage."
    verified, rejected = verify_phrases(
        [{"quote": "No.", "cue": "dismissive"}, {"quote": "No.", "cue": "dismissive"},
         {"quote": "No.", "cue": "dismissive"}, {"quote": "complete garbage", "cue": "insult"},
         {"quote": "garbage", "cue": "insult"}], draft)
    assert [(p["start"], p["end"]) for p in verified] == [(0, 3), (4, 7), (16, 23)]
    assert [p["quote"] for p in rejected] == ["complete garbage"]


def _verdict(**kw):
    base = {"phrases": [], "target": "code", "risk": "low", "rewrite": None}
    return Verdict.model_validate({**base, **kw})


def test_assemble_checks_quotes_and_rewrite():
    draft = "Did you even run this? `getUser()` returns null on 404."
    v = _verdict(phrases=[{"quote": "Did you even run this?", "cue": "condescending"},
                          {"quote": "you are lazy", "cue": "insult"}],
                 target="person", risk="high", rewrite="`getUser()` returns null on 404; please fix it.")
    r = assemble(draft, v)
    assert [p["quote"] for p in r["phrases"]] == ["Did you even run this?"]
    assert len(r["rejected_phrases"]) == 1
    assert r["preservation"]["all_kept"] and r["warnings"] == []
    r = assemble(draft, _verdict(risk="medium", rewrite="Please fix getUser."))
    assert "risk above low but no phrase in the draft supports it" in r["warnings"]
    assert any("dropped technical content" in w for w in r["warnings"])


def test_reassemble_uses_current_checks():
    draft = "This is wrong. `retry_count` resets."
    raw = {"phrases": [{"quote": "This is wrong", "cue": "vague_negative"}], "target": "code",
           "risk": "medium", "rewrite": "`retry_count` resets, which looks incorrect because [reason]."}
    stale = {"draft": draft, "phrases": [], "raw": raw, "llm": {"model": "x"}}
    fresh = reassemble(stale)
    assert fresh["phrases"][0]["quote"] == "This is wrong" and fresh["llm"] == {"model": "x"}


def test_rule_baseline():
    r = rule_check("You are an idiot. `parse()` leaks memory.")
    assert (r["target"], r["risk"]) == ("person", "high")
    r = rule_check("Could you rename `x` to `count`? Thanks.")
    assert r["risk"] == "low" and r["phrases"] == []
    r = rule_check("This is wrong.")
    assert (r["target"], r["risk"]) == ("code", "medium")
    assert rule_check("LGTM, thanks!")["target"] == "none"


def test_f1_and_binary():
    s = f1_scores(["a", "a", "b", "c"], ["a", "b", "b", "c"], ("a", "b", "c", "d"))
    assert s["accuracy"] == 0.75
    assert s["per_class"]["a"]["f1"] == pytest.approx(2 / 3)
    assert s["per_class"]["b"]["f1"] == pytest.approx(2 / 3)
    assert "d" not in s["per_class"]
    assert s["macro_f1"] == pytest.approx((2 / 3 + 2 / 3 + 1) / 3)
    b = binary([True, True, False, False], [True, False, True, False])
    assert (b["tp"], b["fp"], b["fn"], b["tn"]) == (1, 1, 1, 1) and b["f1"] == 0.5


def test_phrase_overlap_is_character_level():
    items = [{"text": "This is wrong. Fix it.", "phrases": ["This is wrong"]}]
    results = [{"phrases": [{"start": 0, "end": 7}]}]  # "This is"
    o = phrase_overlap(items, results)
    assert o["precision"] == 1.0 and o["recall"] == pytest.approx(6 / 11)


@pytest.mark.parametrize("name", ["synthetic_dev.jsonl", "synthetic_test.jsonl"])
def test_gold_sets_are_consistent(name):
    items = load_gold(ROOT / "data/gold" / name)
    assert len({i["id"] for i in items}) == len(items)
    for i in items:
        assert i["source"] == "synthetic"
        assert i["target"] in TARGETS and i["risk"] in RISKS
        assert all(p in i["text"] for p in i["phrases"]), i["id"]
        assert (i["risk"] == "low") == (not i["phrases"]), i["id"]


def test_dev_and_test_do_not_overlap():
    dev = {i["text"] for i in load_gold(ROOT / "data/gold/synthetic_dev.jsonl")}
    test = {i["text"] for i in load_gold(ROOT / "data/gold/synthetic_test.jsonl")}
    assert not dev & test


def test_score_run_and_aggregate():
    items = [{"id": "a", "text": "This is wrong.", "target": "code", "risk": "medium", "phrases": ["This is wrong"]},
             {"id": "b", "text": "LGTM", "target": "none", "risk": "low", "phrases": []}]
    records = [{"result": rule_check(i["text"])} for i in items]
    row = score_run(items, records)
    assert row["labels"]["target"]["accuracy"] == 1.0 and row["failed"] == 0
    s = aggregate([row, row])
    assert s["labels.risk.macro_f1"]["mean"] == row["labels"]["risk"]["macro_f1"]


def test_render_text_and_diff():
    r = rule_check("This is wrong. `retry()` must back off.")
    assert "[[This is wrong]]" in highlight(r["draft"], r["phrases"], color=False)
    assert "Risk:   MEDIUM" in render_text(r)
    assert word_diff("This is wrong", "This looks incorrect", color=False) == "This [-is wrong-] {+looks incorrect+}"


def test_cues_enum_is_closed():
    assert len(CUES) == len(set(CUES)) == 12
    with pytest.raises(ValueError):
        _verdict(phrases=[{"quote": "x", "cue": "angry"}])


def test_demo_samples_are_real_runs():
    """Every sample shown in the web demo must be a stored pipeline output with call metadata."""
    path = ROOT / "web/public/samples.json"
    if not path.exists():
        pytest.skip("demo samples not exported yet")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["samples"]
    for s in data["samples"]:
        assert s["synthetic"] is True and s["outputs"]
        for out in s["outputs"].values():
            assert out["llm"]["request_id"].startswith("req_") and out["llm"]["model"]
            for p in out["phrases"]:
                assert s["text"][p["start"]:p["end"]] == p["quote"]
            if out["rewrite"]:
                assert "".join(x["text"] for x in out["diff"]["left"]) == s["text"]
                assert "".join(x["text"] for x in out["diff"]["right"]) == out["rewrite"]
            for key in ("recheck", "judge"):
                if key in out:
                    assert out[key]["llm"]["request_id"].startswith("req_")
