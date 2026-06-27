# Thai Lottery Analytics Web App

เว็บแอปสำหรับอัปโหลด CSV/XLSX ผลสลากย้อนหลัง แล้วคำนวณ Frequency, Digit Frequency, Heatmap, Probability Matrix, Gap/Cycle, Bayesian Score, Markov Chain, Monte Carlo Simulation, Recency Trend, AI Ranking และ Walk-forward Backtesting

> ผลการวิเคราะห์นี้เป็นการคำนวณเชิงสถิติจากข้อมูลย้อนหลังเท่านั้น ไม่สามารถรับประกันผลรางวัลในอนาคตได้ เพราะการออกรางวัลเป็นเหตุการณ์สุ่มและเป็นอิสระต่อกัน

## Project Structure

```text
backend/
  app/
    main.py
    lottery_analysis.py
    schemas.py
frontend/
  src/
    App.tsx
    lib/api.ts
    types/api.ts
requirements.txt
sample_data.csv
```

## Data Format

ต้องมี columns:

```text
draw_date, first_prize, last2, front3_1, front3_2, back3_1, back3_2
```

ระบบอ่านเลขเป็น string และเติม leading zero อัตโนมัติ เช่น `007`, `009`, `048`

Validation ที่ทำ:

- ตรวจ column ที่ขาด
- ตรวจวันที่ซ้ำ
- ตรวจ null
- `first_prize` ต้อง 6 หลัก
- `last2` ต้อง 2 หลัก
- `front3_*` และ `back3_*` ต้อง 3 หลัก
- sort วันที่จากเก่าไปใหม่

## Backend Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

เปิดเว็บ:

```text
http://localhost:5173
```

Vite proxy จะส่ง `/api/*` ไปที่ `http://127.0.0.1:8000`

## Production / Render Free Deploy

โปรเจกต์นี้ deploy แบบ service เดียวได้: FastAPI serve ทั้ง API และ React build จาก `frontend/dist`

### Test production locally

```bash
cd frontend
npm ci
npm run build
cd ..
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

เปิด:

```text
http://127.0.0.1:8000
```

### Test with Docker

```bash
docker build -t thai-lottery-analyzer .
docker run --rm -p 8000:8000 thai-lottery-analyzer
```

### Deploy to Render Free

1. Push repository ขึ้น GitHub
2. เข้า Render แล้วเลือก `New` -> `Blueprint`
3. เลือก repo นี้
4. Render จะอ่าน `render.yaml`
5. ใช้ plan `free`
6. กด deploy

Render จะใช้:

```text
Dockerfile
render.yaml
.dockerignore
```

หลัง deploy เสร็จจะได้ public URL เช่น:

```text
https://thai-lottery-analyzer.onrender.com
```

Health check:

```text
/health
```

## API

### Sanook Stats Connector

ระบบมี backend proxy สำหรับดึงสถิติย้อนหลังจาก Sanook official endpoint ที่หน้า `news.sanook.com/lotto/lotto-stats/` ใช้งานอยู่:

```bash
curl "http://127.0.0.1:8000/api/sanook/stats?mode=yearly&start_year=2559&end_year=2569"
```

รองรับ:

- `mode=yearly` พร้อม `start_year`, `end_year` เป็น พ.ศ. หรือ ค.ศ.
- `mode=daily` พร้อม `day=sun|mon|tue|wed|thu|fri|sat` และ `year_back`
- `mode=monthly` พร้อม `month=jan|feb|...|dec` และ `year_back`

Response จะ normalize เป็น `rows` ที่มี `category`, `category_label`, `number`, `frequency` โดยคงเลขเป็น string เช่น `007`

### Validate

```bash
curl -F "file=@sample_data.csv" http://127.0.0.1:8000/api/validate
```

### Analyze

```bash
curl \
  -F "file=@sample_data.csv" \
  -F "lottery_type_2d=lower2" \
  -F "lottery_type_3d=all3" \
  -F "monte_carlo_n=100000" \
  http://127.0.0.1:8000/api/analyze
```

### Backtest

```bash
curl \
  -F "file=@sample_data.csv" \
  -F "lottery_type_2d=lower2" \
  -F 'top_n=[3,5,10,20]' \
  http://127.0.0.1:8000/api/backtest
```

### Export

```bash
curl -o lottery_analysis_report.xlsx -F "file=@sample_data.csv" http://127.0.0.1:8000/api/export/xlsx
curl -o lottery_ai_ranking.csv -F "file=@sample_data.csv" http://127.0.0.1:8000/api/export/csv
curl -o lottery_analysis_report.json -F "file=@sample_data.csv" http://127.0.0.1:8000/api/export/json
```

Excel report มี sheets:

- Raw Data
- Clean Data
- Frequency 00-99
- Frequency 000-999
- Digit Frequency
- Probability Matrix
- Bayesian
- Markov
- Monte Carlo
- AI Ranking
- Backtest

## Models Included

- Frequency Analysis สำหรับ 2 ตัวและ 3 ตัว
- Digit Frequency แยกหลัก พร้อม heatmap data
- Heatmap 00-99 และ 000-999
- Probability Matrix: `P(ab)`, `P(ones|tens)`, `P(tens|ones)`
- Gap / Cycle Analysis และ Cycle Score
- Bayesian smoothing ด้วย `alpha = 1`
- Markov Chain 2 ตัว 100x100 พร้อม fallback Bayesian
- Monte Carlo Simulation พร้อม CI95
- Recency Weight ด้วย decay lambda default `0.98`
- Odd/Even และ High/Low patterns
- AI Ranking Score ตาม weight ที่กำหนด
- Walk-forward Backtesting สำหรับ Top 3/5/10/20

## Notes

- ไม่มีการ hardcode ผลหวยจริงในระบบวิเคราะห์
- `sample_data.csv` เป็นข้อมูลตัวอย่างสำหรับทดสอบ format และ flow เท่านั้น
- สำหรับไฟล์ใหญ่ แนะนำเริ่ม Monte Carlo ที่ `100000` ก่อน แล้วค่อยเพิ่มเป็น `1000000`
