"use client";

import { useMemo, useRef, useState } from "react";
import type { DemoData, Output, Phrase, Risk, Sample, Segment, Stat, Target } from "./types";

const TARGET_LABEL: Record<Target, string> = {
  code: "the code",
  person: "the person",
  tool_process: "a tool or process",
  none: "no criticism",
};

const CUE_LABEL: Record<string, string> = {
  person_directed: "aimed at the person",
  insult: "insult",
  profanity: "profanity",
  mocking_or_sarcasm: "mocking or sarcasm",
  dismissive: "dismissive",
  vague_negative: "vague negative",
  absolute_language: "absolute language",
  condescending: "condescending",
  impatience: "impatience",
  blocking_without_reason: "blocks without a reason",
  authority_appeal: "appeal to authority",
  threat: "threat",
};

const SEVERE = new Set(["person_directed", "insult", "threat", "profanity"]);

function RiskBadge({ risk, small }: { risk: Risk; small?: boolean }) {
  return (
    <span className={`badge risk-${risk}${small ? " small" : ""}`}>
      {small ? risk : `${risk} risk`}
    </span>
  );
}

function TargetBadge({ target }: { target: Target }) {
  return <span className={`badge target target-${target}`}>targets {TARGET_LABEL[target]}</span>;
}

function Highlighted({ text, phrases }: { text: string; phrases: Phrase[] }) {
  const parts: React.ReactNode[] = [];
  let pos = 0;
  [...phrases]
    .sort((a, b) => a.start - b.start)
    .forEach((p, i) => {
      if (p.start < pos) return;
      if (p.start > pos) parts.push(text.slice(pos, p.start));
      parts.push(
        <mark key={i} className={SEVERE.has(p.cue) ? "cue severe" : "cue"} title={CUE_LABEL[p.cue] ?? p.cue}>
          {text.slice(p.start, p.end)}
          <span className="cue-tag">{CUE_LABEL[p.cue] ?? p.cue}</span>
        </mark>,
      );
      pos = p.end;
    });
  parts.push(text.slice(pos));
  return <p className="draft">{parts}</p>;
}

function DiffColumn({ title, segments, kind }: { title: string; segments: Segment[]; kind: "del" | "ins" }) {
  return (
    <div className="diff-col">
      <div className="diff-title">{title}</div>
      <p className="draft">
        {segments.map((s, i) =>
          s.changed ? (
            kind === "del" ? <del key={i}>{s.text}</del> : <ins key={i}>{s.text}</ins>
          ) : (
            <span key={i}>{s.text}</span>
          ),
        )}
      </p>
    </div>
  );
}

function money(v: number | null | undefined, digits = 4) {
  return v == null ? "–" : `$${v.toFixed(digits)}`;
}

function Check({ ok, label }: { ok: boolean; label: string }) {
  return (
    <li className={ok ? "ok" : "bad"}>
      <span aria-hidden>{ok ? "✓" : "✗"}</span> {label}
    </li>
  );
}

function OutputView({ sample, out }: { sample: Sample; out: Output }) {
  const goldMatch = out.target === sample.gold.target && out.risk === sample.gold.risk;
  return (
    <div className="output">
      <div className="badges">
        <RiskBadge risk={out.risk} />
        <TargetBadge target={out.target} />
        <span className={`gold ${goldMatch ? "match" : "mismatch"}`}>
          Gold label: {TARGET_LABEL[sample.gold.target]}, {sample.gold.risk} risk {goldMatch ? "✓" : "≠"}
        </span>
      </div>
      {sample.note && <p className="note">Debatable item: {sample.note.replace(/^borderline: /, "")}</p>}

      <h3>Phrases behind the risk</h3>
      <Highlighted text={sample.text} phrases={out.phrases} />
      {out.phrases.length === 0 ? (
        <p className="muted">No phrase flagged.</p>
      ) : (
        <>
          <ul className="phrase-list">
            {[...out.phrases].sort((a, b) => a.start - b.start).map((p, i) => (
              <li key={i}>
                “{p.quote}” <span className="cue-tag">{CUE_LABEL[p.cue] ?? p.cue}</span>
              </li>
            ))}
          </ul>
          <p className="muted small">
            Each quote was found verbatim in the draft
            {out.rejected_phrases.length > 0 && `; ${out.rejected_phrases.length} quote(s) not in the draft were dropped`}.
          </p>
        </>
      )}

      {out.rewrite && out.diff ? (
        <>
          <h3>Suggested rewrite</h3>
          <div className="diff">
            <DiffColumn title="Draft" segments={out.diff.left} kind="del" />
            <DiffColumn title="Rewrite" segments={out.diff.right} kind="ins" />
          </div>
          <div className="checks">
            <div>
              <h4>Technical content (deterministic)</h4>
              {out.tokens && out.tokens.length > 0 ? (
                <ul className="tokens">
                  {out.tokens.map((t, i) => (
                    <li key={i} className={t.kept ? "ok" : "bad"} title={t.kind}>
                      <code>{t.value}</code> {t.kept ? "✓" : "missing"}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted small">No identifiers, code, numbers, paths or URLs in the draft.</p>
              )}
            </div>
            {out.recheck && (
              <div>
                <h4>Rewrite re-checked</h4>
                <p>
                  <RiskBadge risk={out.recheck.risk} small /> {out.recheck.phrases.length > 0 &&
                    <span className="muted small">still flagged: {out.recheck.phrases.map((p) => `“${p.quote}”`).join(", ")}</span>}
                </p>
              </div>
            )}
            {out.judge && (
              <div>
                <h4>Judge ({out.judge.llm.model}, fixed rubric)</h4>
                <ul className="judge">
                  <Check ok={out.judge.technical_points_kept} label="technical points kept" />
                  <Check ok={out.judge.no_added_claims} label="no invented claims" />
                  <Check ok={out.judge.request_strength_kept} label="requests not softened" />
                  <Check ok={out.judge.respectful} label="no disrespect left" />
                </ul>
                {[...out.judge.missing_points, ...out.judge.added_claims, ...out.judge.softened_requests, ...out.judge.disrespect_left].map(
                  (x, i) => <p key={i} className="muted small">• {x}</p>,
                )}
              </div>
            )}
          </div>
        </>
      ) : (
        <p className="muted">No rewrite: the checker rated this draft low risk.</p>
      )}
      {out.warnings.length > 0 && (
        <ul className="warnings">
          {out.warnings.map((w, i) => <li key={i}>Note: {w}</li>)}
        </ul>
      )}
      <p className="meta">
        {out.llm.model} · {out.llm.latency_s.toFixed(1)} s · {money(out.llm.cost_usd, 5)} · request{" "}
        <code>{out.llm.request_id?.slice(0, 16)}…</code>
      </p>
    </div>
  );
}

function fmt(s: Stat | undefined, digits = 2) {
  if (!s) return "–";
  const m = s.mean.toFixed(digits);
  return s.min.toFixed(digits) === s.max.toFixed(digits) ? m : `${m} (${s.min.toFixed(digits)}–${s.max.toFixed(digits)})`;
}

function Results({ data }: { data: DemoData }) {
  if (!data.summary) return null;
  const synth = Object.entries(data.summary).find(([k]) => k.startsWith("synthetic"));
  const tox = Object.entries(data.summary).find(([k]) => k.startsWith("toxicr"));
  return (
    <section className="panel" id="results">
      <h2>Results</h2>
      {synth && (
        <>
          <p className="small muted">
            Synthetic test set: {synth[1].items} comments, {synth[1].runs} runs per model, mean (range). Labels by one
            annotator; see Limitations.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Model</th><th>Target macro-F1</th><th>Risk macro-F1</th><th>Quotes verified</th>
                  <th>Rewrites keep all tokens</th><th>Rewrite re-checked low</th><th>Judge: all four</th>
                  <th>Cost / comment</th><th>Latency (s)</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(synth[1].models).map(([m, s]) => (
                  <tr key={m}>
                    <td><code>{m}</code></td>
                    <td>{fmt(s["labels.target.macro_f1"])}</td>
                    <td>{fmt(s["labels.risk.macro_f1"])}</td>
                    <td>{fmt(s["labels.phrase_validity"])}</td>
                    <td>{fmt(s["rewrites.tokens_all_kept"])}</td>
                    <td>{fmt(s["rewrites.after_low"])}</td>
                    <td>{fmt(s["rewrites.judge_pass"])}</td>
                    <td>{s["cost_per_comment_usd"] ? `$${s["cost_per_comment_usd"].mean.toFixed(5)}` : "$0"}</td>
                    <td>{fmt(s["latency_mean_s"], 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {tox && (
        <>
          <p className="small muted">
            Human-labelled code review comments (ToxiCR sample): {tox[1].items} comments, {tox[1].runs} run(s). Agreement
            of “medium or high risk” with the human toxic label.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Model</th><th>Precision</th><th>Recall</th><th>F1</th><th>“High” vs toxic F1</th><th>Quotes verified</th></tr>
              </thead>
              <tbody>
                {Object.entries(tox[1].models).map(([m, s]) => (
                  <tr key={m}>
                    <td><code>{m}</code></td>
                    <td>{fmt(s["toxicity.flag_vs_toxic.precision"])}</td>
                    <td>{fmt(s["toxicity.flag_vs_toxic.recall"])}</td>
                    <td>{fmt(s["toxicity.flag_vs_toxic.f1"])}</td>
                    <td>{fmt(s["toxicity.high_vs_toxic.f1"])}</td>
                    <td>{fmt(s["toxicity.phrase_validity"])}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

export default function Demo({ data, basis, limitations }: { data: DemoData; basis: React.ReactNode; limitations: React.ReactNode }) {
  const [model, setModel] = useState(data.models.includes("gpt-6.1-terra") ? "gpt-6.1-terra" : data.models[0]);
  const [filter, setFilter] = useState<"all" | Risk>("all");
  const [selected, setSelected] = useState(data.samples[0]?.id);
  const visible = useMemo(
    () => data.samples.filter((s) => filter === "all" || s.outputs[model]?.risk === filter),
    [data.samples, filter, model],
  );
  const sample = data.samples.find((s) => s.id === selected) ?? visible[0];
  const mainRef = useRef<HTMLElement>(null);
  const pick = (id: string) => {
    setSelected(id);
    // On narrow screens the result sits below the list; bring it into view.
    if (window.matchMedia("(max-width: 860px)").matches) {
      requestAnimationFrame(() => mainRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    }
  };
  const out = sample?.outputs[model];

  return (
    <main>
      <header>
        <h1>PR Tone Coach</h1>
        <p className="lede">
          Check your own code review comment before you post it: who the criticism targets, the exact phrases that may read
          as an attack or as pushback, and a rewrite that keeps every technical point.
        </p>
        <p className="demo-note">
          Demo mode: no API key needed. The comments are <strong>synthetic</strong> (written for this project), and every
          output below is a stored result of a real pipeline run on them, not hand-written. Labels describe the text of a
          comment, never the person who wrote it.
        </p>
      </header>

      <div className="layout">
        <aside>
          <div className="controls">
            <label>
              Model
              <select value={model} onChange={(e) => setModel(e.target.value)}>
                {data.models.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </label>
            <div className="filters" role="group" aria-label="Filter by risk">
              {(["all", "high", "medium", "low"] as const).map((f) => (
                <button key={f} className={filter === f ? "on" : ""} onClick={() => setFilter(f)}>{f}</button>
              ))}
            </div>
          </div>
          <ul className="samples">
            {visible.map((s) => (
              <li key={s.id}>
                <button className={s.id === sample?.id ? "on" : ""} onClick={() => pick(s.id)}>
                  {s.outputs[model] && <RiskBadge risk={s.outputs[model].risk} small />}
                  <span className="sample-text">{s.text}</span>
                </button>
              </li>
            ))}
            {visible.length === 0 && <li className="muted small">No comment at this risk level for {model}.</li>}
          </ul>
        </aside>

        <section className="main" ref={mainRef}>
          {sample && out ? (
            <>
              <div className="sample-head">
                <span className="badge synthetic">synthetic</span>
                <span className="muted small">{sample.id} · output of {model}</span>
              </div>
              <OutputView sample={sample} out={out} />
            </>
          ) : (
            <p className="muted">Pick a comment.</p>
          )}
        </section>
      </div>

      <Results data={data} />

      <section className="panel" id="cli">
        <h2>Try it on your own draft</h2>
        <p>The checker is a Python CLI. It reads the draft, prints the result, and never posts anything.</p>
        <pre>{`uv sync
uv run prtone check "Did you even run this? getUser() returns null on 404."
uv run prtone check --file draft.md --model gpt-6.1-terra --recheck
uv run prtone check --file draft.md --rules   # keyword baseline, no API key`}</pre>
      </section>

      <div className="two-col">
        <section className="panel" id="research">
          <h2>Research basis</h2>
          {basis}
        </section>
        <section className="panel" id="limitations">
          <h2>Limitations</h2>
          {limitations}
        </section>
      </div>
      <footer className="muted small">Source data: {data.source}. Built from the systematic mapping study “Emotions in Software Engineering”.</footer>
    </main>
  );
}
