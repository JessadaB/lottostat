from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://news.sanook.com/ajax/lotto/lotto-stats"
SOURCE_PAGE = "https://news.sanook.com/lotto/lotto-stats/"

TABLE_LABELS = {
    "last2": "เลขท้าย 2 ตัวล่าง",
    "jackpot2": "เลขท้ายรางวัลที่ 1 (2 ตัวบน)",
    "last3": "เลขท้าย 3 ตัว",
    "jackpot3": "เลขท้ายรางวัลที่ 1 (3 ตัวบน)",
    "first3": "เลขหน้า 3 ตัว",
}

DAY_MAP = {
    "sun": "sunday",
    "mon": "monday",
    "tue": "tuesday",
    "wed": "wednesday",
    "thu": "thursday",
    "fri": "friday",
    "sat": "saturday",
}

MONTH_MAP = {
    "jan": "01",
    "feb": "02",
    "mar": "03",
    "apr": "04",
    "may": "05",
    "jun": "06",
    "jul": "07",
    "aug": "08",
    "sep": "09",
    "oct": "10",
    "nov": "11",
    "dec": "12",
}


def _be_to_ad(year: int) -> int:
    return year - 543 if year > 2400 else year


def _read_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 ThaiLotteryAnalytics/1.0",
            "Accept": "application/json,text/javascript,*/*;q=0.8",
            "Referer": SOURCE_PAGE,
        },
    )
    with urlopen(request, timeout=15) as response:
        text = response.read().decode("utf-8")
    text = text.strip()
    if text.startswith(("callback(", "jQuery")):
        match = re.search(r"^[^(]+\((.*)\)\s*;?$", text, flags=re.S)
        if match:
            text = match.group(1)
    return json.loads(text)


def _flatten(data: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for category, groups in data.items():
        for group in groups:
            frequency = int(group.get("frequency", 0))
            for number in group.get("number", []):
                rows.append(
                    {
                        "category": category,
                        "category_label": TABLE_LABELS.get(category, category),
                        "number": str(number).zfill(3 if category in {"last3", "jackpot3", "first3"} else 2),
                        "frequency": frequency,
                    }
                )
    rows.sort(key=lambda row: (row["category"], -row["frequency"], row["number"]))
    return rows


def fetch_sanook_stats(
    mode: str = "yearly",
    start_year: int = 2559,
    end_year: int = 2569,
    day: str = "sun",
    month: str = "jan",
    year_back: int = 10,
) -> dict[str, Any]:
    mode = mode.lower()
    if mode == "yearly":
        endpoint = f"{BASE_URL}/getbyyear/"
        params = {"start_year": _be_to_ad(start_year), "end_year": _be_to_ad(end_year)}
        display = f"พ.ศ. {start_year} - {end_year}"
    elif mode == "daily":
        endpoint = f"{BASE_URL}/getbydaily/"
        params = {"day": DAY_MAP.get(day, day), "year_back": year_back}
        display = f"วัน {day} ย้อนหลัง {year_back} ปี"
    elif mode == "monthly":
        endpoint = f"{BASE_URL}/getbymonth/"
        params = {"month": MONTH_MAP.get(month, month), "year_back": year_back}
        display = f"เดือน {month} ย้อนหลัง {year_back} ปี"
    else:
        raise ValueError("mode ต้องเป็น yearly, daily หรือ monthly")

    url = f"{endpoint}?{urlencode(params)}"
    payload = _read_json(url)
    data = payload.get("data", {})
    return {
        "source": "Sanook Lotto Stats",
        "source_url": url,
        "source_page": SOURCE_PAGE,
        "mode": mode,
        "display_range": display,
        "tables": data,
        "rows": _flatten(data),
        "categories": TABLE_LABELS,
    }
