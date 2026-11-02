export type Risk = "low" | "medium" | "high";
export type Target = "code" | "person" | "tool_process" | "none";

export interface Llm {
  model: string;
  request_id: string | null;
  latency_s: number;
  cost_usd: number | null;
  input_tokens: number;
  cached_input_tokens: number;
  output_tokens: number;
}

export interface Phrase {
  quote: string;
  cue: string;
  start: number;
  end: number;
}

export interface Segment {
  text: string;
  changed: boolean;
}

export interface Judge {
  missing_points: string[];
  added_claims: string[];
  softened_requests: string[];
  disrespect_left: string[];
  technical_points_kept: boolean;
  no_added_claims: boolean;
  request_strength_kept: boolean;
  respectful: boolean;
  pass: boolean;
  llm: Llm;
}

export interface Output {
  target: Target;
  risk: Risk;
  phrases: Phrase[];
  rejected_phrases: string[];
  rewrite: string | null;
  warnings: string[];
  llm: Llm;
  tokens?: { kind: string; value: string; kept: boolean }[];
  diff?: { left: Segment[]; right: Segment[] };
  recheck?: { risk: Risk; target: Target; phrases: { quote: string; cue: string }[]; llm: Llm };
  judge?: Judge;
}

export interface Sample {
  id: string;
  synthetic: boolean;
  text: string;
  gold: { target: Target; risk: Risk; phrases: string[] };
  note: string | null;
  outputs: Record<string, Output>;
}

export type Stat = { mean: number; min: number; max: number };

export interface SummaryTable {
  items: number;
  runs: number;
  models: Record<string, Record<string, Stat>>;
}

export interface DemoData {
  source: string;
  models: string[];
  samples: Sample[];
  summary: Record<string, SummaryTable> | null;
}
