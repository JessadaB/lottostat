import { useMemo, useState } from "react";
import { Activity, BarChart3, Download, FileSpreadsheet, Flame, Grid3X3, LineChart, Play, RadioTower, Upload } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Line, LineChart as ReLineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { analyzeFile, backtestFile, downloadExport, fetchSanookStats, validateFile } from "./lib/api";
import type { AnalysisResult, BacktestResult, RankRow, SanookStatsResult } from "./types/api";

const tabs = [
  "Upload Data",
  "Dashboard",
  "Frequency",
  "Heatmap",
  "Probability Matrix",
  "Markov",
  "Bayesian",
  "Monte Carlo",
  "AI Ranking",
  "Backtesting",
  "Sanook API"
];

const warning =
  "ผลการวิเคราะห์นี้เป็นการคำนวณเชิงสถิติจากข้อมูลย้อนหลังเท่านั้น ไม่สามารถรับประกันผลรางวัลในอนาคตได้ เพราะการออกรางวัลเป็นเหตุการณ์สุ่มและเป็นอิสระต่อกัน";

function pct(value?: number) {
  return `${((value ?? 0) * 100).toFixed(3)}%`;
}

function score(value?: number) {
  return ((value ?? 0) * 100).toFixed(2);
}

function topRows(rows: RankRow[] = [], count = 20) {
  return rows.slice(0, count);
}

function Card({ title, value, tone }: { title: string; value: string | number; tone?: string }) {
  return (
    <div className="border border-line bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</p>
      <p className={`mt-2 text-2xl font-bold ${tone ?? "text-ink"}`}>{value}</p>
    </div>
  );
}

function DataTable({ rows, columns, maxHeight = "max-h-96" }: { rows: Record<string, unknown>[]; columns: string[]; maxHeight?: string }) {
  return (
    <div className={`overflow-auto border border-line bg-white ${maxHeight} scrollbar-thin`}>
      <table className="min-w-full border-collapse text-sm">
        <thead className="sticky top-0 bg-panel text-left text-xs uppercase text-neutral-500">
          <tr>
            {columns.map((column) => (
              <th className="border-b border-line px-3 py-2 font-semibold" key={column}>
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr className="odd:bg-white even:bg-panel/70" key={index}>
              {columns.map((column) => (
                <td className="whitespace-nowrap border-b border-line px-3 py-2" key={column}>
                  {typeof row[column] === "number" ? Number(row[column]).toFixed(column.includes("score") || column.includes("prob") || column.includes("rate") ? 6 : 0) : String(row[column] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Heatmap2D({ matrix }: { matrix: number[][] }) {
  const max = Math.max(1, ...matrix.flat());
  return (
    <div className="grid w-full max-w-xl grid-cols-10 border border-line bg-white">
      {matrix.flatMap((row, r) =>
        row.map((value, c) => {
          const alpha = 0.08 + (value / max) * 0.82;
          return (
            <div
              key={`${r}-${c}`}
              className="flex aspect-square min-w-0 items-center justify-center border-b border-r border-line text-xs font-semibold"
              style={{ backgroundColor: `rgba(31, 157, 120, ${alpha})` }}
              title={`${r}${c}: ${value}`}
            >
              {r}
              {c}
            </div>
          );
        })
      )}
    </div>
  );
}

function MatrixTable({ matrix, label }: { matrix: number[][]; label: string }) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-bold">{label}</h3>
      <div className="overflow-auto border border-line bg-white scrollbar-thin">
        <table className="min-w-[720px] text-xs">
          <thead className="bg-panel">
            <tr>
              <th className="px-2 py-2">row</th>
              {Array.from({ length: 10 }, (_, i) => (
                <th className="px-2 py-2" key={i}>
                  {i}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, index) => (
              <tr className="odd:bg-white even:bg-panel/70" key={index}>
                <td className="px-2 py-1 font-semibold">{index}</td>
                {row.map((value, col) => (
                  <td className="px-2 py-1" key={col}>
                    {value.toFixed(4)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState(tabs[0]);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Record<string, string>[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [backtest, setBacktest] = useState<BacktestResult | null>(null);
  const [lotteryType2d, setLotteryType2d] = useState("lower2");
  const [lotteryType3d, setLotteryType3d] = useState("all3");
  const [simulations, setSimulations] = useState(100000);
  const [sanookStats, setSanookStats] = useState<SanookStatsResult | null>(null);
  const [sanookMode, setSanookMode] = useState<"yearly" | "daily" | "monthly">("yearly");
  const [sanookStartYear, setSanookStartYear] = useState(2559);
  const [sanookEndYear, setSanookEndYear] = useState(2569);
  const [sanookDay, setSanookDay] = useState("sun");
  const [sanookMonth, setSanookMonth] = useState("jan");
  const [sanookYearBack, setSanookYearBack] = useState(10);
  const [loading, setLoading] = useState(false);

  const frequencyChart = useMemo(() => topRows(analysis?.frequency.two_digit ?? [], 10).map((row) => ({ number: row.number, count: row.count })), [analysis]);
  const aiChart = useMemo(() => topRows(analysis?.ai_ranking.two_digit ?? [], 10).map((row) => ({ number: row.number, score: Number(score(row.ai_score)) })), [analysis]);
  const sanookChart = useMemo(
    () =>
      (sanookStats?.rows ?? [])
        .filter((row) => row.category === "last2")
        .slice(0, 12)
        .map((row) => ({ number: row.number, frequency: row.frequency })),
    [sanookStats]
  );

  async function handleFile(nextFile: File) {
    setFile(nextFile);
    setAnalysis(null);
    setBacktest(null);
    setErrors([]);
    setWarnings([]);
    setLoading(true);
    try {
      const result = await validateFile(nextFile);
      setPreview(result.preview);
      setErrors(result.errors);
      setWarnings(result.warnings);
    } catch (error) {
      setErrors([error instanceof Error ? error.message : "Validate failed"]);
    } finally {
      setLoading(false);
    }
  }

  async function runAnalysis() {
    if (!file) return;
    setLoading(true);
    setErrors([]);
    try {
      const result = await analyzeFile(file, {
        lottery_type_2d: lotteryType2d,
        lottery_type_3d: lotteryType3d,
        monte_carlo_n: simulations
      });
      setAnalysis(result);
      setWarnings(result.warnings);
      setActiveTab("Dashboard");
    } catch (error) {
      setErrors([error instanceof Error ? error.message : "Analyze failed"]);
    } finally {
      setLoading(false);
    }
  }

  async function runBacktest() {
    if (!file) return;
    setLoading(true);
    try {
      const result = await backtestFile(file, { lottery_type_2d: lotteryType2d, top_n: "[3,5,10,20]", start_after: 10 });
      setBacktest(result);
      setActiveTab("Backtesting");
    } catch (error) {
      setErrors([error instanceof Error ? error.message : "Backtest failed"]);
    } finally {
      setLoading(false);
    }
  }

  async function exportReport(type: "xlsx" | "csv" | "json") {
    if (!file) return;
    setLoading(true);
    try {
      await downloadExport(file, type, { lottery_type_2d: lotteryType2d, lottery_type_3d: lotteryType3d, monte_carlo_n: simulations });
    } catch (error) {
      setErrors([error instanceof Error ? error.message : "Export failed"]);
    } finally {
      setLoading(false);
    }
  }

  async function loadSanookStats() {
    setLoading(true);
    setErrors([]);
    try {
      const result = await fetchSanookStats({
        mode: sanookMode,
        start_year: sanookStartYear,
        end_year: sanookEndYear,
        day: sanookDay,
        month: sanookMonth,
        year_back: sanookYearBack
      });
      setSanookStats(result);
      setActiveTab("Sanook API");
    } catch (error) {
      setErrors([error instanceof Error ? error.message : "Sanook API failed"]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase text-mint">Thai Lottery Analytics</p>
            <h1 className="text-2xl font-bold">วิเคราะห์สถิติหวยไทยจากข้อมูลย้อนหลัง</h1>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="inline-flex items-center gap-2 border border-line bg-panel px-3 py-2 text-sm font-semibold" onClick={loadSanookStats} disabled={loading}>
              <RadioTower size={16} /> Sanook
            </button>
            <button className="inline-flex items-center gap-2 border border-line bg-panel px-3 py-2 text-sm font-semibold" onClick={() => exportReport("xlsx")} disabled={!file || loading}>
              <FileSpreadsheet size={16} /> Excel
            </button>
            <button className="inline-flex items-center gap-2 border border-line bg-panel px-3 py-2 text-sm font-semibold" onClick={() => exportReport("csv")} disabled={!file || loading}>
              <Download size={16} /> CSV
            </button>
            <button className="inline-flex items-center gap-2 border border-line bg-panel px-3 py-2 text-sm font-semibold" onClick={() => exportReport("json")} disabled={!file || loading}>
              <Download size={16} /> JSON
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-4 px-4 py-5 lg:grid-cols-[230px_1fr]">
        <aside className="border border-line bg-white p-2">
          {tabs.map((tab) => (
            <button
              className={`block w-full px-3 py-2 text-left text-sm font-semibold ${activeTab === tab ? "bg-ink text-white" : "hover:bg-panel"}`}
              key={tab}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          ))}
        </aside>

        <section className="space-y-4">
          <div className="border border-amber/40 bg-white p-4 text-sm font-semibold text-ink">{analysis?.metadata.warning ?? warning}</div>

          {(errors.length > 0 || warnings.length > 0) && (
            <div className="grid gap-2 md:grid-cols-2">
              {errors.length > 0 && <div className="border border-coral bg-white p-3 text-sm text-coral">{errors.join(" | ")}</div>}
              {warnings.length > 0 && <div className="border border-amber bg-white p-3 text-sm text-amber">{warnings.join(" | ")}</div>}
            </div>
          )}

          {activeTab === "Upload Data" && (
            <div className="grid gap-4 xl:grid-cols-[1fr_1.4fr]">
              <div className="border border-line bg-white p-5">
                <div className="flex items-center gap-2 text-lg font-bold">
                  <Upload size={20} /> Upload CSV/XLSX
                </div>
                <input
                  className="mt-4 block w-full border border-line bg-panel p-3"
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={(event) => event.target.files?.[0] && handleFile(event.target.files[0])}
                />
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <label className="text-sm font-semibold">
                    2 ตัว
                    <select className="mt-1 w-full border border-line bg-white p-2" value={lotteryType2d} onChange={(event) => setLotteryType2d(event.target.value)}>
                      <option value="lower2">2 ตัวล่าง</option>
                      <option value="upper2">2 ตัวบน</option>
                    </select>
                  </label>
                  <label className="text-sm font-semibold">
                    3 ตัว
                    <select className="mt-1 w-full border border-line bg-white p-2" value={lotteryType3d} onChange={(event) => setLotteryType3d(event.target.value)}>
                      <option value="all3">รวมทั้งหมด</option>
                      <option value="upper3">3 ตัวบน</option>
                      <option value="front3">หน้า 3 ตัว</option>
                      <option value="back3">ท้าย 3 ตัว</option>
                    </select>
                  </label>
                  <label className="text-sm font-semibold">
                    Simulation N
                    <input className="mt-1 w-full border border-line bg-white p-2" type="number" min="1000" max="1000000" value={simulations} onChange={(event) => setSimulations(Number(event.target.value))} />
                  </label>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button className="inline-flex items-center gap-2 bg-mint px-4 py-2 font-bold text-white disabled:opacity-50" disabled={!file || loading || errors.length > 0} onClick={runAnalysis}>
                    <Play size={16} /> Analyze
                  </button>
                  <button className="inline-flex items-center gap-2 border border-line bg-panel px-4 py-2 font-bold disabled:opacity-50" disabled={!file || loading || errors.length > 0} onClick={runBacktest}>
                    <Activity size={16} /> Backtest
                  </button>
                  <button className="inline-flex items-center gap-2 border border-amber bg-panel px-4 py-2 font-bold text-amber disabled:opacity-50" disabled={loading} onClick={loadSanookStats}>
                    <RadioTower size={16} /> ดึงสถิติ Sanook
                  </button>
                </div>
              </div>
              <div>
                <h2 className="mb-2 text-lg font-bold">Preview Data</h2>
                <DataTable rows={preview} columns={Object.keys(preview[0] ?? {})} />
              </div>
            </div>
          )}

          {activeTab === "Dashboard" && analysis && (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-4">
                <Card title="จำนวนงวด" value={analysis.metadata.total_draws} />
                <Card title="ช่วงวันที่" value={`${analysis.metadata.date_start} ถึง ${analysis.metadata.date_end}`} />
                <Card title="เลขล่าสุด" value={analysis.metadata.latest_draw.last2 ?? "-"} tone="text-mint" />
                <Card title="Markov Last State" value={analysis.markov.last_state ?? "-"} tone="text-coral" />
              </div>
              <div className="grid gap-4 xl:grid-cols-2">
                <div className="border border-line bg-white p-4">
                  <h2 className="mb-3 flex items-center gap-2 font-bold"><Flame size={18} /> Top 10 AI Ranking</h2>
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={aiChart}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="number" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="score" fill="#1f9d78" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="border border-line bg-white p-4">
                  <h2 className="mb-3 font-bold">Top 3 เด่น / Top 3 เลี่ยง</h2>
                  <div className="grid gap-3 md:grid-cols-2">
                    <DataTable rows={analysis.ai_ranking.top3 as Record<string, unknown>[]} columns={["rank", "number", "ai_score"]} maxHeight="max-h-56" />
                    <DataTable rows={analysis.ai_ranking.avoid3 as Record<string, unknown>[]} columns={["number", "ai_score", "avoid_reason"]} maxHeight="max-h-56" />
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "Frequency" && analysis && (
            <div className="space-y-4">
              <div className="border border-line bg-white p-4">
                <h2 className="mb-3 flex items-center gap-2 font-bold"><BarChart3 size={18} /> Frequency 00-99</h2>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={frequencyChart}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="number" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#d96459" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <DataTable rows={analysis.frequency.two_digit as Record<string, unknown>[]} columns={["rank", "number", "count", "probability"]} />
              <DataTable rows={topRows(analysis.frequency.three_digit, 100) as Record<string, unknown>[]} columns={["rank", "number", "count", "probability"]} />
            </div>
          )}

          {activeTab === "Heatmap" && analysis && (
            <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
              <div className="border border-line bg-white p-4">
                <h2 className="mb-3 flex items-center gap-2 font-bold"><Grid3X3 size={18} /> Heatmap 00-99</h2>
                <Heatmap2D matrix={analysis.heatmap.two_digit} />
              </div>
              <div className="border border-line bg-white p-4">
                <h2 className="mb-3 font-bold">Heatmap 000-999 แบบ 100x10</h2>
                <div className="grid max-h-[520px] grid-cols-10 overflow-auto border border-line scrollbar-thin">
                  {analysis.heatmap.three_digit.matrix_100x10.flatMap((row, r) => row.map((value, c) => <div className="border-b border-r border-line p-1 text-center text-[10px]" key={`${r}-${c}`}>{String(r).padStart(2, "0")}{c}<br />{value}</div>))}
                </div>
              </div>
            </div>
          )}

          {activeTab === "Probability Matrix" && analysis && (
            <div className="space-y-4">
              <MatrixTable label="P(ab)" matrix={analysis.probability_matrix.p_ab} />
              <MatrixTable label="P(ones | tens)" matrix={analysis.probability_matrix.p_ones_given_tens} />
              <MatrixTable label="P(tens | ones)" matrix={analysis.probability_matrix.p_tens_given_ones} />
            </div>
          )}

          {activeTab === "Markov" && analysis && (
            <div className="space-y-4">
              <Card title="Last State" value={analysis.markov.last_state ?? "-"} />
              <DataTable rows={analysis.markov.top_candidates as unknown as Record<string, unknown>[]} columns={["number", "markov_probability"]} />
              <MatrixTable label="Transition Probability 100x100 (แสดง 10 คอลัมน์แรกต่อแถว)" matrix={analysis.markov.transition_prob.map((row) => row.slice(0, 10)).slice(0, 100)} />
            </div>
          )}

          {activeTab === "Bayesian" && analysis && (
            <div className="space-y-4">
              <DataTable rows={analysis.bayesian.two_digit as Record<string, unknown>[]} columns={["bayesian_rank", "number", "posterior_probability"]} />
              <DataTable rows={topRows(analysis.bayesian.three_digit, 100) as Record<string, unknown>[]} columns={["bayesian_rank", "number", "posterior_probability"]} />
            </div>
          )}

          {activeTab === "Monte Carlo" && analysis && (
            <div className="space-y-4">
              <div className="border border-line bg-white p-4">
                <button className="inline-flex items-center gap-2 bg-mint px-4 py-2 font-bold text-white disabled:opacity-50" disabled={!file || loading} onClick={runAnalysis}>
                  <Play size={16} /> Run {simulations.toLocaleString()} simulations
                </button>
              </div>
              <DataTable rows={topRows(analysis.monte_carlo.two_digit, 100) as Record<string, unknown>[]} columns={["monte_carlo_rank", "number", "sim_probability", "ci95_low", "ci95_high"]} />
            </div>
          )}

          {activeTab === "AI Ranking" && analysis && (
            <div className="space-y-4">
              <DataTable rows={analysis.ai_ranking.two_digit as Record<string, unknown>[]} columns={["rank", "number", "ai_score", "frequency_score", "bayesian_score", "markov_score", "cycle_score", "recency_score", "monte_carlo_score", "avoid_reason"]} />
              <DataTable rows={topRows(analysis.ai_ranking.three_digit, 100) as Record<string, unknown>[]} columns={["rank", "number", "ai_score", "frequency_score", "bayesian_score", "cycle_score", "recency_score", "monte_carlo_score"]} />
            </div>
          )}

          {activeTab === "Backtesting" && (
            <div className="space-y-4">
              <div className="border border-line bg-white p-4">
                <button className="inline-flex items-center gap-2 bg-ink px-4 py-2 font-bold text-white disabled:opacity-50" disabled={!file || loading} onClick={runBacktest}>
                  <LineChart size={16} /> Run Walk-forward Backtest
                </button>
              </div>
              {backtest && (
                <>
                  <div className="grid gap-3 md:grid-cols-4">
                    {Object.entries(backtest.summary).map(([key, value]) => <Card key={key} title={key} value={pct(value)} />)}
                  </div>
                  <div className="border border-line bg-white p-4">
                    <ResponsiveContainer width="100%" height={260}>
                      <ReLineChart data={backtest.performance}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="model" />
                        <YAxis tickFormatter={(value) => `${Number(value) * 100}%`} />
                        <Tooltip formatter={(value) => pct(Number(value))} />
                        <Line type="monotone" dataKey="hit_rate_top3" stroke="#d96459" />
                        <Line type="monotone" dataKey="hit_rate_top10" stroke="#1f9d78" />
                        <Line type="monotone" dataKey="hit_rate_top20" stroke="#d99b31" />
                      </ReLineChart>
                    </ResponsiveContainer>
                  </div>
                  <DataTable rows={backtest.performance as Record<string, unknown>[]} columns={Object.keys(backtest.performance[0] ?? {})} />
                  <DataTable rows={backtest.rows as Record<string, unknown>[]} columns={Object.keys(backtest.rows[0] ?? {})} />
                </>
              )}
            </div>
          )}

          {activeTab === "Sanook API" && (
            <div className="space-y-4">
              <div className="border border-line bg-white p-5">
                <h2 className="mb-3 flex items-center gap-2 text-lg font-bold text-amber"><RadioTower size={20} /> Sanook Lotto Stats API</h2>
                <div className="grid gap-3 md:grid-cols-5">
                  <label className="text-sm font-semibold">
                    Mode
                    <select className="mt-1 w-full border border-line bg-white p-2" value={sanookMode} onChange={(event) => setSanookMode(event.target.value as "yearly" | "daily" | "monthly")}>
                      <option value="yearly">สถิติทั้งหมดตามปี</option>
                      <option value="daily">สถิติตามวัน</option>
                      <option value="monthly">สถิติตามเดือน</option>
                    </select>
                  </label>
                  <label className="text-sm font-semibold">
                    Start พ.ศ.
                    <input className="mt-1 w-full border border-line bg-white p-2" type="number" value={sanookStartYear} onChange={(event) => setSanookStartYear(Number(event.target.value))} />
                  </label>
                  <label className="text-sm font-semibold">
                    End พ.ศ.
                    <input className="mt-1 w-full border border-line bg-white p-2" type="number" value={sanookEndYear} onChange={(event) => setSanookEndYear(Number(event.target.value))} />
                  </label>
                  <label className="text-sm font-semibold">
                    Day / Month
                    {sanookMode === "monthly" ? (
                      <select className="mt-1 w-full border border-line bg-white p-2" value={sanookMonth} onChange={(event) => setSanookMonth(event.target.value)}>
                        {["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"].map((month) => <option key={month} value={month}>{month}</option>)}
                      </select>
                    ) : (
                      <select className="mt-1 w-full border border-line bg-white p-2" value={sanookDay} onChange={(event) => setSanookDay(event.target.value)}>
                        {["sun", "mon", "tue", "wed", "thu", "fri", "sat"].map((day) => <option key={day} value={day}>{day}</option>)}
                      </select>
                    )}
                  </label>
                  <label className="text-sm font-semibold">
                    Year Back
                    <input className="mt-1 w-full border border-line bg-white p-2" type="number" min="1" max="20" value={sanookYearBack} onChange={(event) => setSanookYearBack(Number(event.target.value))} />
                  </label>
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <button className="inline-flex items-center gap-2 bg-amber px-4 py-2 font-bold text-black disabled:opacity-50" disabled={loading} onClick={loadSanookStats}>
                    <Play size={16} /> Load Sanook Stats
                  </button>
                  {sanookStats && (
                    <a className="text-sm font-semibold text-mint underline" href={sanookStats.source_page} target="_blank" rel="noreferrer">
                      Official Sanook source
                    </a>
                  )}
                </div>
              </div>

              {sanookStats && (
                <>
                  <div className="grid gap-3 md:grid-cols-4">
                    <Card title="Source" value={sanookStats.source} tone="text-amber" />
                    <Card title="Mode" value={sanookStats.mode} />
                    <Card title="Range" value={sanookStats.display_range} />
                    <Card title="Rows" value={sanookStats.rows.length} tone="text-mint" />
                  </div>
                  <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
                    <div className="border border-line bg-white p-4">
                      <h3 className="mb-3 font-bold text-amber">Top เลขท้าย 2 ตัวล่าง จาก Sanook</h3>
                      <ResponsiveContainer width="100%" height={260}>
                        <BarChart data={sanookChart}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="number" />
                          <YAxis allowDecimals={false} />
                          <Tooltip />
                          <Bar dataKey="frequency" fill="#f59e0b" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <DataTable rows={sanookStats.rows.slice(0, 160) as unknown as Record<string, unknown>[]} columns={["category_label", "number", "frequency"]} />
                  </div>
                </>
              )}
            </div>
          )}

          {!analysis && activeTab !== "Upload Data" && activeTab !== "Backtesting" && activeTab !== "Sanook API" && (
            <div className="border border-line bg-white p-6 text-center font-semibold">อัปโหลดไฟล์และกด Analyze ก่อนใช้งานหน้านี้</div>
          )}
        </section>
      </div>
    </main>
  );
}
