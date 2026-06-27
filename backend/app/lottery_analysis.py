from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from math import sqrt
from typing import Any

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = [
    "draw_date",
    "first_prize",
    "last2",
    "front3_1",
    "front3_2",
    "back3_1",
    "back3_2",
]

TWO_DIGIT_TYPES = {
    "upper2": "2 ตัวบน",
    "lower2": "2 ตัวล่าง",
}

THREE_DIGIT_TYPES = {
    "upper3": "3 ตัวบน",
    "front3": "เลขหน้า 3 ตัว",
    "back3": "เลขท้าย 3 ตัว",
    "all3": "รวม 3 ตัวทั้งหมด",
}


@dataclass
class CleanResult:
    frame: pd.DataFrame
    warnings: list[str]
    errors: list[str]


def number_space(length: int) -> list[str]:
    return [str(i).zfill(length) for i in range(10**length)]


def normalize_score(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    arr = np.array(list(values.values()), dtype=float)
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    min_v = float(arr.min())
    max_v = float(arr.max())
    if max_v - min_v <= 1e-15:
        return {key: 0.0 for key in values}
    return {key: float((value - min_v) / (max_v - min_v)) for key, value in values.items()}


def read_upload(contents: bytes, filename: str) -> pd.DataFrame:
    buffer = BytesIO(contents)
    if filename.lower().endswith(".csv"):
        return pd.read_csv(buffer, dtype=str)
    if filename.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(buffer, dtype=str, engine="openpyxl")
    raise ValueError("รองรับเฉพาะไฟล์ CSV, XLSX, XLS")


def _clean_number(value: Any, length: int) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    text = "".join(ch for ch in text if ch.isdigit())
    if not text:
        return None
    return text.zfill(length)


def clean_and_validate(df: pd.DataFrame) -> CleanResult:
    warnings: list[str] = []
    errors: list[str] = []
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        return CleanResult(pd.DataFrame(), warnings, [f"ขาด column: {', '.join(missing)}"])

    clean = df[REQUIRED_COLUMNS].copy()
    clean["draw_date"] = pd.to_datetime(clean["draw_date"], errors="coerce")
    if clean["draw_date"].isna().any():
        errors.append("พบวันที่ไม่ถูกต้องหรือว่าง")

    duplicate_dates = clean["draw_date"].dropna().duplicated().sum()
    if duplicate_dates:
        warnings.append(f"พบวันที่ซ้ำ {int(duplicate_dates)} รายการ ระบบเก็บไว้เพื่อวิเคราะห์แต่แจ้งเตือนให้ตรวจสอบ")

    lengths = {
        "first_prize": 6,
        "last2": 2,
        "front3_1": 3,
        "front3_2": 3,
        "back3_1": 3,
        "back3_2": 3,
    }
    for col, length in lengths.items():
        clean[col] = clean[col].map(lambda value: _clean_number(value, length))
        if clean[col].isna().any():
            errors.append(f"พบค่า null หรือไม่ใช่ตัวเลขใน {col}")
        invalid = clean[col].dropna().map(len).ne(length).sum()
        if invalid:
            errors.append(f"{col} ต้องมี {length} หลัก พบผิด {int(invalid)} รายการ")

    clean = clean.sort_values("draw_date").reset_index(drop=True)
    clean["upper2"] = clean["first_prize"].str[-2:]
    clean["upper3"] = clean["first_prize"].str[-3:]
    clean["draw_date"] = clean["draw_date"].dt.strftime("%Y-%m-%d")
    return CleanResult(clean, warnings, errors)


def get_2d_series(df: pd.DataFrame, lottery_type: str) -> list[str]:
    if lottery_type == "upper2":
        return df["upper2"].dropna().astype(str).str.zfill(2).tolist()
    return df["last2"].dropna().astype(str).str.zfill(2).tolist()


def get_3d_series(df: pd.DataFrame, lottery_type: str) -> list[str]:
    if lottery_type == "upper3":
        cols = ["upper3"]
    elif lottery_type == "front3":
        cols = ["front3_1", "front3_2"]
    elif lottery_type == "back3":
        cols = ["back3_1", "back3_2"]
    else:
        cols = ["upper3", "front3_1", "front3_2", "back3_1", "back3_2"]
    values: list[str] = []
    for col in cols:
        values.extend(df[col].dropna().astype(str).str.zfill(3).tolist())
    return values


def frequency_table(values: list[str], length: int) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, float]]:
    states = number_space(length)
    counts = {state: 0 for state in states}
    for value in values:
        if value in counts:
            counts[value] += 1
    total = max(len(values), 1)
    probs = {state: counts[state] / total for state in states}
    ordered = sorted(states, key=lambda state: (-counts[state], state))
    rank = {state: index + 1 for index, state in enumerate(ordered)}
    rows = [
        {"number": state, "count": counts[state], "probability": probs[state], "rank": rank[state]}
        for state in states
    ]
    return rows, counts, probs


def digit_frequency(values: list[str], length: int) -> dict[str, Any]:
    positions = ["hundreds", "tens", "ones"] if length == 3 else ["tens", "ones"]
    rows: list[dict[str, Any]] = []
    matrix = {position: {str(digit): 0 for digit in range(10)} for position in positions}
    total = max(len(values), 1)
    for value in values:
        padded = value.zfill(length)
        for index, position in enumerate(positions):
            matrix[position][padded[index]] += 1
    for position in positions:
        for digit in range(10):
            count = matrix[position][str(digit)]
            rows.append(
                {
                    "position": position,
                    "digit": str(digit),
                    "count": count,
                    "probability": count / total,
                }
            )
    return {"rows": rows, "matrix": matrix}


def heatmap_2d(counts: dict[str, int]) -> list[list[int]]:
    return [[counts[f"{row}{col}"] for col in range(10)] for row in range(10)]


def heatmap_3d(counts: dict[str, int]) -> dict[str, Any]:
    matrix_100x10 = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for prefix in range(100):
        row_key = str(prefix).zfill(2)
        matrix_100x10.append([counts[f"{row_key}{col}"] for col in range(10)])
    for group in range(10):
        start = group * 100
        label = f"{start:03d}-{start + 99:03d}"
        grouped[label] = [
            {"number": f"{number:03d}", "count": counts[f"{number:03d}"]}
            for number in range(start, start + 100)
        ]
    return {"matrix_100x10": matrix_100x10, "groups": grouped}


def probability_matrices(counts: dict[str, int], total_draws: int) -> dict[str, list[list[float]]]:
    total = max(total_draws, 1)
    tens_counts = {str(d): 0 for d in range(10)}
    ones_counts = {str(d): 0 for d in range(10)}
    for number, count in counts.items():
        tens_counts[number[0]] += count
        ones_counts[number[1]] += count
    p_ab: list[list[float]] = []
    p_ones_given_tens: list[list[float]] = []
    p_tens_given_ones: list[list[float]] = []
    for tens in range(10):
        p_row = []
        ogt_row = []
        tgo_row = []
        for ones in range(10):
            count = counts[f"{tens}{ones}"]
            p_row.append(count / total)
            ogt_row.append(count / tens_counts[str(tens)] if tens_counts[str(tens)] else 0)
            tgo_row.append(count / ones_counts[str(ones)] if ones_counts[str(ones)] else 0)
        p_ab.append(p_row)
        p_ones_given_tens.append(ogt_row)
        p_tens_given_ones.append(tgo_row)
    return {
        "p_ab": p_ab,
        "p_ones_given_tens": p_ones_given_tens,
        "p_tens_given_ones": p_tens_given_ones,
    }


def gap_cycle(values: list[str], length: int) -> tuple[list[dict[str, Any]], dict[str, float]]:
    states = number_space(length)
    total = len(values)
    rows: list[dict[str, Any]] = []
    scores: dict[str, float] = {}
    for state in states:
        positions = [index for index, value in enumerate(values) if value == state]
        if not positions:
            last_seen_gap = total
            avg_gap = None
            max_gap = None
            min_gap = None
            cycle_score = 0.0
        else:
            last_seen_gap = total - 1 - positions[-1]
            gaps = np.diff(positions)
            if len(gaps):
                avg_gap = float(np.mean(gaps))
                max_gap = int(np.max(gaps))
                min_gap = int(np.min(gaps))
                cycle_score = 1 - abs(last_seen_gap - avg_gap) / max(avg_gap, 1)
                cycle_score = float(min(max(cycle_score, 0), 1))
            else:
                avg_gap = None
                max_gap = None
                min_gap = None
                cycle_score = 0.0
        scores[state] = cycle_score
        rows.append(
            {
                "number": state,
                "last_seen_gap": last_seen_gap,
                "avg_gap": avg_gap,
                "max_gap": max_gap,
                "min_gap": min_gap,
                "cycle_score": cycle_score,
            }
        )
    return rows, scores


def bayesian(counts: dict[str, int], total_events: int, length: int, alpha: float = 1.0) -> tuple[list[dict[str, Any]], dict[str, float]]:
    states = number_space(length)
    k = 10**length
    posterior = {state: (counts[state] + alpha) / (total_events + alpha * k) for state in states}
    ordered = sorted(states, key=lambda state: (-posterior[state], state))
    rank = {state: index + 1 for index, state in enumerate(ordered)}
    rows = [
        {"number": state, "posterior_probability": posterior[state], "bayesian_rank": rank[state]}
        for state in states
    ]
    return rows, posterior


def markov_2d(values: list[str], fallback_prob: dict[str, float]) -> dict[str, Any]:
    states = number_space(2)
    index = {state: i for i, state in enumerate(states)}
    counts = np.zeros((100, 100), dtype=int)
    for current, nxt in zip(values[:-1], values[1:]):
        if current in index and nxt in index:
            counts[index[current], index[nxt]] += 1
    probs = np.zeros((100, 100), dtype=float)
    for row_index, state in enumerate(states):
        row_sum = counts[row_index].sum()
        if row_sum:
            probs[row_index] = counts[row_index] / row_sum
        else:
            probs[row_index] = np.array([fallback_prob[target] for target in states])
    last_state = values[-1] if values else None
    scores = {state: fallback_prob[state] for state in states}
    if last_state in index:
        scores = {state: float(probs[index[last_state], index[state]]) for state in states}
    top = sorted(states, key=lambda state: (-scores[state], state))[:20]
    return {
        "last_state": last_state,
        "transition_counts": counts.tolist(),
        "transition_prob": probs.tolist(),
        "top_candidates": [{"number": state, "markov_probability": scores[state]} for state in top],
        "scores": scores,
    }


def monte_carlo(counts: dict[str, int], total_events: int, length: int, simulations: int, seed: int) -> tuple[list[dict[str, Any]], dict[str, float]]:
    states = number_space(length)
    _, posterior = bayesian(counts, total_events, length)
    weights = np.array([posterior[state] for state in states], dtype=float)
    weights = weights / weights.sum()
    rng = np.random.default_rng(seed)
    samples = rng.choice(states, size=simulations, p=weights)
    sample_counts = pd.Series(samples).value_counts().to_dict()
    rows: list[dict[str, Any]] = []
    sim_scores: dict[str, float] = {}
    for state in states:
        count = int(sample_counts.get(state, 0))
        p = count / simulations
        se = sqrt(p * (1 - p) / simulations)
        sim_scores[state] = p
        rows.append(
            {
                "number": state,
                "sim_count": count,
                "sim_probability": p,
                "ci95_low": max(0.0, p - 1.96 * se),
                "ci95_high": min(1.0, p + 1.96 * se),
            }
        )
    ordered = sorted(states, key=lambda state: (-sim_scores[state], state))
    ranks = {state: index + 1 for index, state in enumerate(ordered)}
    for row in rows:
        row["monte_carlo_rank"] = ranks[row["number"]]
    return rows, sim_scores


def recency_weight(values: list[str], length: int, decay_lambda: float) -> tuple[list[dict[str, Any]], dict[str, float]]:
    states = number_space(length)
    weighted_counts = {state: 0.0 for state in states}
    total = len(values)
    total_weight = 0.0
    for index, value in enumerate(values):
        weight = decay_lambda ** (total - 1 - index)
        total_weight += weight
        if value in weighted_counts:
            weighted_counts[value] += weight
    denom = total_weight or 1.0
    probs = {state: weighted_counts[state] / denom for state in states}
    ordered = sorted(states, key=lambda state: (-probs[state], state))
    ranks = {state: index + 1 for index, state in enumerate(ordered)}
    rows = [
        {
            "number": state,
            "weighted_count": weighted_counts[state],
            "weighted_probability": probs[state],
            "recency_rank": ranks[state],
        }
        for state in states
    ]
    return rows, probs


def odd_even_high_low(values: list[str]) -> dict[str, Any]:
    last_digit = {"odd": 0, "even": 0}
    digit_balance = {"odd_digits": 0, "even_digits": 0, "high_digits": 0, "low_digits": 0}
    patterns: dict[str, int] = {}
    high_low_patterns: dict[str, int] = {}
    for value in values:
        digits = [int(ch) for ch in value.zfill(2)]
        last_digit["odd" if digits[-1] % 2 else "even"] += 1
        oe_pattern = "".join("O" if digit % 2 else "E" for digit in digits)
        hl_pattern = "".join("H" if digit >= 5 else "L" for digit in digits)
        patterns[oe_pattern] = patterns.get(oe_pattern, 0) + 1
        high_low_patterns[hl_pattern] = high_low_patterns.get(hl_pattern, 0) + 1
        for digit in digits:
            digit_balance["odd_digits" if digit % 2 else "even_digits"] += 1
            digit_balance["high_digits" if digit >= 5 else "low_digits"] += 1
    total = max(len(values), 1)
    total_digits = max(len(values) * 2, 1)
    return {
        "last_digit": {key: {"count": value, "ratio": value / total} for key, value in last_digit.items()},
        "digit_balance": {key: {"count": value, "ratio": value / total_digits} for key, value in digit_balance.items()},
        "odd_even_patterns": patterns,
        "high_low_patterns": high_low_patterns,
    }


def ai_ranking(
    states: list[str],
    frequency: dict[str, float],
    bayes: dict[str, float],
    markov: dict[str, float] | None,
    cycle: dict[str, float],
    recency: dict[str, float],
    monte: dict[str, float],
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    base_weights = weights or {
        "frequency": 0.20,
        "bayesian": 0.20,
        "markov": 0.20,
        "cycle": 0.15,
        "recency": 0.15,
        "monte_carlo": 0.10,
    }
    if markov is None:
        base_weights = base_weights.copy()
        share = base_weights.get("markov", 0) / 2
        base_weights["frequency"] += share
        base_weights["bayesian"] += share
        base_weights["markov"] = 0
        markov = {state: 0.0 for state in states}
    score_maps = {
        "frequency": normalize_score(frequency),
        "bayesian": normalize_score(bayes),
        "markov": normalize_score(markov),
        "cycle": normalize_score(cycle),
        "recency": normalize_score(recency),
        "monte_carlo": normalize_score(monte),
    }
    total_weight = sum(base_weights.values()) or 1
    rows: list[dict[str, Any]] = []
    for state in states:
        score = sum(base_weights[key] * score_maps[key].get(state, 0.0) for key in score_maps) / total_weight
        low_reasons = []
        if score_maps["frequency"].get(state, 0) < 0.25:
            low_reasons.append("frequency ต่ำ")
        if score_maps["cycle"].get(state, 0) < 0.25:
            low_reasons.append("ไม่เข้า cycle")
        if score_maps["recency"].get(state, 0) < 0.25:
            low_reasons.append("recency ต่ำ")
        if score_maps["markov"].get(state, 0) < 0.25:
            low_reasons.append("markov ต่ำ")
        rows.append(
            {
                "number": state,
                "ai_score": float(score),
                "frequency_score": score_maps["frequency"].get(state, 0.0),
                "bayesian_score": score_maps["bayesian"].get(state, 0.0),
                "markov_score": score_maps["markov"].get(state, 0.0),
                "cycle_score": score_maps["cycle"].get(state, 0.0),
                "recency_score": score_maps["recency"].get(state, 0.0),
                "monte_carlo_score": score_maps["monte_carlo"].get(state, 0.0),
                "avoid_reason": ", ".join(low_reasons) if low_reasons else "คะแนนรวมต่ำเมื่อเทียบกับตัวอื่น",
            }
        )
    rows.sort(key=lambda row: (-row["ai_score"], row["number"]))
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def analyze_dataframe(
    df: pd.DataFrame,
    lottery_type_2d: str = "lower2",
    lottery_type_3d: str = "all3",
    monte_carlo_n: int = 100000,
    decay_lambda: float = 0.98,
    random_seed: int = 42,
) -> dict[str, Any]:
    clean_result = clean_and_validate(df)
    if clean_result.errors:
        return {"errors": clean_result.errors, "warnings": clean_result.warnings}
    clean = clean_result.frame
    values_2d = get_2d_series(clean, lottery_type_2d)
    values_3d = get_3d_series(clean, lottery_type_3d)

    freq_2d, counts_2d, probs_2d = frequency_table(values_2d, 2)
    freq_3d, counts_3d, probs_3d = frequency_table(values_3d, 3)
    digit_2d = digit_frequency(values_2d, 2)
    digit_3d = digit_frequency(values_3d, 3)
    cycle_2d_rows, cycle_2d_scores = gap_cycle(values_2d, 2)
    cycle_3d_rows, cycle_3d_scores = gap_cycle(values_3d, 3)
    bayes_2d_rows, bayes_2d = bayesian(counts_2d, len(values_2d), 2)
    bayes_3d_rows, bayes_3d = bayesian(counts_3d, len(values_3d), 3)
    markov = markov_2d(values_2d, bayes_2d)
    monte_2d_rows, monte_2d = monte_carlo(counts_2d, len(values_2d), 2, monte_carlo_n, random_seed)
    monte_3d_rows, monte_3d = monte_carlo(counts_3d, len(values_3d), 3, min(monte_carlo_n, 300000), random_seed)
    recency_2d_rows, recency_2d = recency_weight(values_2d, 2, decay_lambda)
    recency_3d_rows, recency_3d = recency_weight(values_3d, 3, decay_lambda)
    ai_2d = ai_ranking(number_space(2), probs_2d, bayes_2d, markov["scores"], cycle_2d_scores, recency_2d, monte_2d)
    ai_3d = ai_ranking(number_space(3), probs_3d, bayes_3d, None, cycle_3d_scores, recency_3d, monte_3d)
    latest = clean.iloc[-1].to_dict() if len(clean) else {}
    avoid_2d = sorted(ai_2d, key=lambda row: (row["ai_score"], row["number"]))[:20]

    return {
        "errors": [],
        "warnings": clean_result.warnings,
        "metadata": {
            "total_draws": len(clean),
            "date_start": clean["draw_date"].iloc[0] if len(clean) else None,
            "date_end": clean["draw_date"].iloc[-1] if len(clean) else None,
            "latest_draw": latest,
            "lottery_type_2d": lottery_type_2d,
            "lottery_type_3d": lottery_type_3d,
            "warning": "ผลการวิเคราะห์นี้เป็นการคำนวณเชิงสถิติจากข้อมูลย้อนหลังเท่านั้น ไม่สามารถรับประกันผลรางวัลในอนาคตได้ เพราะการออกรางวัลเป็นเหตุการณ์สุ่มและเป็นอิสระต่อกัน",
        },
        "clean_data": clean.to_dict(orient="records"),
        "frequency": {"two_digit": freq_2d, "three_digit": freq_3d},
        "digit_frequency": {"two_digit": digit_2d, "three_digit": digit_3d},
        "heatmap": {"two_digit": heatmap_2d(counts_2d), "three_digit": heatmap_3d(counts_3d)},
        "probability_matrix": probability_matrices(counts_2d, len(values_2d)),
        "cycle": {
            "two_digit": cycle_2d_rows,
            "three_digit": cycle_3d_rows,
            "longest_missing": sorted(cycle_2d_rows, key=lambda row: (-row["last_seen_gap"], row["number"]))[:10],
            "frequent_cycle": sorted(cycle_2d_rows, key=lambda row: (row["avg_gap"] is None, row["avg_gap"] or 10**9, row["number"]))[:10],
        },
        "bayesian": {"two_digit": bayes_2d_rows, "three_digit": bayes_3d_rows},
        "markov": markov,
        "monte_carlo": {"two_digit": monte_2d_rows, "three_digit": monte_3d_rows},
        "recency": {
            "two_digit": recency_2d_rows,
            "three_digit": recency_3d_rows,
            "hot_numbers": sorted(recency_2d_rows, key=lambda row: (-row["weighted_probability"], row["number"]))[:10],
            "cold_numbers": sorted(recency_2d_rows, key=lambda row: (row["weighted_probability"], row["number"]))[:10],
        },
        "patterns": odd_even_high_low(values_2d),
        "ai_ranking": {
            "two_digit": ai_2d,
            "three_digit": ai_3d,
            "top3": ai_2d[:3],
            "avoid3": avoid_2d[:3],
            "top10": ai_2d[:10],
            "top20": ai_2d[:20],
        },
    }


def backtest_dataframe(df: pd.DataFrame, top_n: list[int], lottery_type_2d: str = "lower2", start_after: int = 10) -> dict[str, Any]:
    clean_result = clean_and_validate(df)
    if clean_result.errors:
        return {"errors": clean_result.errors, "warnings": clean_result.warnings}
    clean = clean_result.frame
    actual_values = get_2d_series(clean, lottery_type_2d)
    top_n = sorted(set(top_n))
    hits = {n: 0 for n in top_n}
    trials = 0
    rows: list[dict[str, Any]] = []
    model_hits = {
        "frequency": {n: 0 for n in top_n},
        "bayesian": {n: 0 for n in top_n},
        "ai": {n: 0 for n in top_n},
    }
    for i in range(max(start_after, 1), len(clean)):
        train = clean.iloc[:i]
        actual = actual_values[i]
        result = analyze_dataframe(train, lottery_type_2d=lottery_type_2d, monte_carlo_n=10000)
        if result.get("errors"):
            continue
        trials += 1
        ai_rank = [row["number"] for row in result["ai_ranking"]["two_digit"]]
        freq_rank = [row["number"] for row in sorted(result["frequency"]["two_digit"], key=lambda row: (row["rank"], row["number"]))]
        bayes_rank = [row["number"] for row in sorted(result["bayesian"]["two_digit"], key=lambda row: (row["bayesian_rank"], row["number"]))]
        row = {"draw_date": clean.iloc[i]["draw_date"], "actual": actual}
        for n in top_n:
            hit = actual in ai_rank[:n]
            hits[n] += int(hit)
            model_hits["ai"][n] += int(hit)
            model_hits["frequency"][n] += int(actual in freq_rank[:n])
            model_hits["bayesian"][n] += int(actual in bayes_rank[:n])
            row[f"hit_top{n}"] = hit
        rows.append(row)
    summary = {f"hit_rate_top{n}": (hits[n] / trials if trials else 0) for n in top_n}
    performance = [
        {
            "model": model,
            **{f"hit_rate_top{n}": (values[n] / trials if trials else 0) for n in top_n},
        }
        for model, values in model_hits.items()
    ]
    return {
        "errors": [],
        "warnings": clean_result.warnings,
        "trials": trials,
        "summary": summary,
        "performance": performance,
        "rows": rows,
    }


def build_excel_report(raw_df: pd.DataFrame, analysis: dict[str, Any], backtest: dict[str, Any] | None = None) -> BytesIO:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        raw_df.to_excel(writer, sheet_name="Raw Data", index=False)
        pd.DataFrame(analysis.get("clean_data", [])).to_excel(writer, sheet_name="Clean Data", index=False)
        pd.DataFrame(analysis["frequency"]["two_digit"]).to_excel(writer, sheet_name="Frequency 00-99", index=False)
        pd.DataFrame(analysis["frequency"]["three_digit"]).to_excel(writer, sheet_name="Frequency 000-999", index=False)
        pd.DataFrame(analysis["digit_frequency"]["two_digit"]["rows"]).to_excel(writer, sheet_name="Digit Frequency", index=False)
        matrix_rows = []
        for name, matrix in analysis["probability_matrix"].items():
            for row_index, row in enumerate(matrix):
                matrix_rows.append({"matrix": name, "row": row_index, **{str(i): value for i, value in enumerate(row)}})
        pd.DataFrame(matrix_rows).to_excel(writer, sheet_name="Probability Matrix", index=False)
        pd.DataFrame(analysis["bayesian"]["two_digit"]).to_excel(writer, sheet_name="Bayesian", index=False)
        pd.DataFrame(analysis["markov"]["top_candidates"]).to_excel(writer, sheet_name="Markov", index=False)
        pd.DataFrame(analysis["monte_carlo"]["two_digit"]).to_excel(writer, sheet_name="Monte Carlo", index=False)
        pd.DataFrame(analysis["ai_ranking"]["two_digit"]).to_excel(writer, sheet_name="AI Ranking", index=False)
        if backtest:
            pd.DataFrame(backtest.get("rows", [])).to_excel(writer, sheet_name="Backtest", index=False)
        else:
            pd.DataFrame().to_excel(writer, sheet_name="Backtest", index=False)
    output.seek(0)
    return output
