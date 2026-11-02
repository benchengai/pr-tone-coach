import Demo from "./Demo";
import samples from "../public/samples.json";
import type { DemoData } from "./types";

const basis = (
  <>
    <p>
      In the source mapping study (57 studies), the cell <em>Communication &amp; Collaboration × Design/Implementation</em>{" "}
      has 0 studies. Code review research exists, but the study files work that mines review comments after the fact under
      Maintenance. This tool sits earlier: the author checks a comment while writing it, before anyone reads it.
    </p>
    <p>The labels and cue types are grounded in, not validated by, this work:</p>
    <ul>
      <li>
        <strong>Pushback.</strong> Egelman et al. (ICSE 2020; an included study) define pushback as the perception of
        unnecessary interpersonal conflict while a reviewer blocks a change. They detect it from review logs, not text. →
        the <em>risk</em> framing and the <em>blocking without reason</em> cue.
      </li>
      <li>
        <strong>Destructive criticism.</strong> Gunawardena et al. (CSCW 2022) call negative feedback destructive when it is
        both nonspecific and inconsiderate (harsh or sarcastic, threatening, or blaming the person). → <em>vague
        negative</em>, <em>mocking or sarcasm</em> and <em>aimed at the person</em>; blunt but specific feedback stays low risk.
      </li>
      <li>
        <strong>Incivility and toxicity.</strong> Ferreira et al. (CSCW 2021) coded uncivil features in Linux kernel review
        emails, among them impatience, irony, mocking, name calling, threats and vulgarity. Sarker et al.&apos;s ToxiCR (TOSEM
        2023) labels review comments toxic for insults, threats, personal attacks or swearing, and ToxiSpanSE (ESEM 2023)
        marks the toxic words. → the <em>impatience</em>, <em>insult</em>, <em>threat</em> and <em>profanity</em> cues,
        and the held-out human-labelled test sample.
      </li>
      <li>
        <strong>Direction.</strong> Gachechiladze et al. (ICSE NIER 2017; an included study) separated anger aimed at oneself,
        at others and at objects in Apache Jira comments, and found most of it aimed at objects such as tools or code. →
        the <em>target</em> label.
      </li>
      <li>
        <strong>Closest prior tools.</strong> Rahman et al. (FSE 2024) generate civil alternatives to uncivil review
        comments; ToxiShield (Anindya et al., FSE 2026) filters toxic comments and rewrites them in real time. This tool
        adds the target, pushback beyond toxicity, quotes checked against the draft, and a deterministic check that the
        rewrite keeps every technical token.
      </li>
      <li>
        <strong>Cues, not emotions.</strong> Barrett et al. (2019) show that emotional states cannot be reliably inferred
        from facial movements. The tool takes the same caution with text: it reports features of phrases, such as a
        condescending phrase, never how the writer feels.
      </li>
      <li>
        <strong>Law.</strong> The EU AI Act, Art. 5(1)(f), prohibits AI that infers the emotions of people at work. The tool
        is a writing aid the author runs on their own draft: it labels text, keeps no history and scores no one.
      </li>
    </ul>
  </>
);

const limitations = (
  <ul>
    <li>
      The demo comments and their gold labels are synthetic and come from one annotator, who also wrote the prompt.
      Agreement on them is an optimistic smoke test, not a benchmark.
    </li>
    {/* EXTERNAL-LIMITATION */}
    <li>
      Pushback and destructive criticism are perceptions of the recipient. The checker sees only the text: not the
      relationship, the history of the change or the team&apos;s norms. A comment that is fine in one team can sting in another.
    </li>
    <li>
      The rewrite judge is an LLM from the same provider as the checked models (and the same model as one of them). Its
      verdicts were spot-checked by hand, not fully verified.
    </li>
    <li>
      The token check is necessary, not sufficient: it does not see plain names such as “Jenkins” or numbers written as
      words. The judge covers meaning.
    </li>
    <li>“Risk after rewrite” is rated by the model that wrote the rewrite.</li>
    <li>Mostly English comments; one German item.</li>
    <li>
      The LLM checker sends the draft to the OpenAI API. Do not paste secrets; the keyword baseline (<code>--rules</code>)
      runs offline.
    </li>
    <li>No user study: there is no evidence yet that rewrites change how comments are received.</li>
  </ul>
);

export default function Page() {
  return <Demo data={samples as unknown as DemoData} basis={basis} limitations={limitations} />;
}
