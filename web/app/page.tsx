import Demo from "./Demo";
import samples from "../public/samples.json";
import type { DemoData } from "./types";

const basis = (
  <>
    <p>
      In the source mapping study (57 studies), the cell <em>Communication &amp; Collaboration × Design/Implementation</em>{" "}
      has 0 studies. Code review research exists, but the study files work that mines review comments after the fact under
      Maintenance. This tool sits earlier: the author checks a comment while writing it.
    </p>
    <p>PLACEHOLDER: verified references are added after citation checks.</p>
  </>
);

const limitations = (
  <ul>
    <li>PLACEHOLDER</li>
  </ul>
);

export default function Page() {
  return <Demo data={samples as unknown as DemoData} basis={basis} limitations={limitations} />;
}
