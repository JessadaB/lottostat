from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .lottery_analysis import (
    analyze_dataframe,
    backtest_dataframe,
    build_excel_report,
    clean_and_validate,
    read_upload,
)
from .sanook_client import fetch_sanook_stats


app = FastAPI(title="Thai Lottery Analytics API", version="1.0.0")
ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIST_DIR = ROOT_DIR / "frontend" / "dist"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/sanook/stats")
def sanook_stats(
    mode: str = "yearly",
    start_year: int = 2559,
    end_year: int = 2569,
    day: str = "sun",
    month: str = "jan",
    year_back: int = 10,
) -> JSONResponse:
    try:
        result = fetch_sanook_stats(
            mode=mode,
            start_year=start_year,
            end_year=end_year,
            day=day,
            month=month,
            year_back=year_back,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ดึงข้อมูล Sanook ไม่สำเร็จ: {exc}") from exc
    return JSONResponse(result)


async def _load_upload(file: UploadFile) -> pd.DataFrame:
    contents = await file.read()
    try:
        return read_upload(contents, file.filename or "upload.csv")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/validate")
async def validate_file(file: UploadFile = File(...)) -> JSONResponse:
    df = await _load_upload(file)
    result = clean_and_validate(df)
    preview = result.frame.head(20).to_dict(orient="records") if not result.frame.empty else []
    return JSONResponse(
        {
            "errors": result.errors,
            "warnings": result.warnings,
            "preview": preview,
            "columns": list(df.columns),
            "total_rows": len(df),
        }
    )


@app.post("/api/analyze")
async def analyze_file(
    file: UploadFile = File(...),
    lottery_type_2d: str = Form("lower2"),
    lottery_type_3d: str = Form("all3"),
    monte_carlo_n: int = Form(100000),
    decay_lambda: float = Form(0.98),
    random_seed: int = Form(42),
) -> JSONResponse:
    df = await _load_upload(file)
    result = analyze_dataframe(
        df,
        lottery_type_2d=lottery_type_2d,
        lottery_type_3d=lottery_type_3d,
        monte_carlo_n=monte_carlo_n,
        decay_lambda=decay_lambda,
        random_seed=random_seed,
    )
    if result.get("errors"):
        return JSONResponse(result, status_code=422)
    return JSONResponse(result)


@app.post("/api/backtest")
async def backtest_file(
    file: UploadFile = File(...),
    lottery_type_2d: str = Form("lower2"),
    top_n: str = Form("[3,5,10,20]"),
    start_after: int = Form(10),
) -> JSONResponse:
    df = await _load_upload(file)
    try:
        parsed_top_n = [int(value) for value in json.loads(top_n)]
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="top_n ต้องเป็น JSON array เช่น [3,5,10,20]") from exc
    result = backtest_dataframe(df, parsed_top_n, lottery_type_2d=lottery_type_2d, start_after=start_after)
    if result.get("errors"):
        return JSONResponse(result, status_code=422)
    return JSONResponse(result)


@app.post("/api/export/{export_type}")
async def export_file(
    export_type: str,
    file: UploadFile = File(...),
    lottery_type_2d: str = Form("lower2"),
    lottery_type_3d: str = Form("all3"),
    monte_carlo_n: int = Form(100000),
) -> StreamingResponse:
    df = await _load_upload(file)
    analysis = analyze_dataframe(
        df,
        lottery_type_2d=lottery_type_2d,
        lottery_type_3d=lottery_type_3d,
        monte_carlo_n=monte_carlo_n,
    )
    if analysis.get("errors"):
        raise HTTPException(status_code=422, detail=analysis["errors"])

    if export_type == "xlsx":
        backtest = backtest_dataframe(df, [3, 5, 10, 20], lottery_type_2d=lottery_type_2d)
        report = build_excel_report(df, analysis, backtest)
        return StreamingResponse(
            report,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="lottery_analysis_report.xlsx"'},
        )

    if export_type == "json":
        payload = json.dumps(analysis, ensure_ascii=False).encode("utf-8")
        return StreamingResponse(
            iter([payload]),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="lottery_analysis_report.json"'},
        )

    if export_type == "csv":
        buffer = StringIO()
        pd.DataFrame(analysis["ai_ranking"]["two_digit"]).to_csv(buffer, index=False)
        buffer.seek(0)
        return StreamingResponse(
            iter([buffer.getvalue().encode("utf-8-sig")]),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="lottery_ai_ranking.csv"'},
        )

    raise HTTPException(status_code=400, detail="export_type ต้องเป็น xlsx, csv หรือ json")


if FRONTEND_DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST_DIR, html=True), name="frontend")
