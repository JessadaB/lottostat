export type RankRow = {
  number: string;
  rank?: number;
  count?: number;
  probability?: number;
  posterior_probability?: number;
  bayesian_rank?: number;
  ai_score?: number;
  frequency_score?: number;
  bayesian_score?: number;
  markov_score?: number;
  cycle_score?: number;
  recency_score?: number;
  monte_carlo_score?: number;
  avoid_reason?: string;
  sim_probability?: number;
  ci95_low?: number;
  ci95_high?: number;
};

export type AnalysisResult = {
  errors: string[];
  warnings: string[];
  metadata: {
    total_draws: number;
    date_start: string;
    date_end: string;
    latest_draw: Record<string, string>;
    warning: string;
  };
  clean_data: Record<string, string>[];
  frequency: { two_digit: RankRow[]; three_digit: RankRow[] };
  digit_frequency: {
    two_digit: { rows: Record<string, string | number>[]; matrix: Record<string, Record<string, number>> };
    three_digit: { rows: Record<string, string | number>[]; matrix: Record<string, Record<string, number>> };
  };
  heatmap: { two_digit: number[][]; three_digit: { matrix_100x10: number[][]; groups: Record<string, { number: string; count: number }[]> } };
  probability_matrix: {
    p_ab: number[][];
    p_ones_given_tens: number[][];
    p_tens_given_ones: number[][];
  };
  cycle: {
    two_digit: RankRow[];
    longest_missing: Record<string, string | number | null>[];
    frequent_cycle: Record<string, string | number | null>[];
  };
  bayesian: { two_digit: RankRow[]; three_digit: RankRow[] };
  markov: {
    last_state: string;
    transition_prob: number[][];
    top_candidates: { number: string; markov_probability: number }[];
  };
  monte_carlo: { two_digit: RankRow[]; three_digit: RankRow[] };
  recency: {
    hot_numbers: Record<string, string | number>[];
    cold_numbers: Record<string, string | number>[];
  };
  patterns: Record<string, unknown>;
  ai_ranking: {
    two_digit: RankRow[];
    three_digit: RankRow[];
    top3: RankRow[];
    avoid3: RankRow[];
    top10: RankRow[];
    top20: RankRow[];
  };
};

export type BacktestResult = {
  errors: string[];
  trials: number;
  summary: Record<string, number>;
  performance: Record<string, string | number>[];
  rows: Record<string, string | boolean>[];
};

export type SanookStatsRow = {
  category: string;
  category_label: string;
  number: string;
  frequency: number;
};

export type SanookStatsResult = {
  source: string;
  source_url: string;
  source_page: string;
  mode: "yearly" | "daily" | "monthly";
  display_range: string;
  tables: Record<string, { frequency: number; number: string[] }[]>;
  rows: SanookStatsRow[];
  categories: Record<string, string>;
};
