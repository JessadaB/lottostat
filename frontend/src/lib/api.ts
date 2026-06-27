import type { AnalysisResult, BacktestResult, SanookStatsResult } from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

function buildForm(file: File, extra?: Record<string, string | number>) {
  const form = new FormData();
  form.append("file", file);
  Object.entries(extra ?? {}).forEach(([key, value]) => form.append(key, String(value)));
  return form;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const data = await response.json();
  if (!response.ok) {
    const message = Array.isArray(data.detail) ? data.detail.join(", ") : data.detail ?? data.errors?.join(", ") ?? "Request failed";
    throw new Error(message);
  }
  return data as T;
}

export async function validateFile(file: File) {
  const response = await fetch(`${API_BASE}/api/validate`, { method: "POST", body: buildForm(file) });
  return parseResponse<{ errors: string[]; warnings: string[]; preview: Record<string, string>[]; total_rows: number }>(response);
}

export async function analyzeFile(file: File, options: Record<string, string | number>) {
  const response = await fetch(`${API_BASE}/api/analyze`, { method: "POST", body: buildForm(file, options) });
  return parseResponse<AnalysisResult>(response);
}

export async function backtestFile(file: File, options: Record<string, string | number>) {
  const response = await fetch(`${API_BASE}/api/backtest`, { method: "POST", body: buildForm(file, options) });
  return parseResponse<BacktestResult>(response);
}

export async function downloadExport(file: File, type: "xlsx" | "csv" | "json", options: Record<string, string | number>) {
  const response = await fetch(`${API_BASE}/api/export/${type}`, { method: "POST", body: buildForm(file, options) });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail ?? "Export failed");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = type === "xlsx" ? "lottery_analysis_report.xlsx" : type === "json" ? "lottery_analysis_report.json" : "lottery_ai_ranking.csv";
  link.click();
  URL.revokeObjectURL(url);
}

export async function fetchSanookStats(options: Record<string, string | number>) {
  const params = new URLSearchParams();
  Object.entries(options).forEach(([key, value]) => params.set(key, String(value)));
  const response = await fetch(`${API_BASE}/api/sanook/stats?${params.toString()}`);
  return parseResponse<SanookStatsResult>(response);
}
