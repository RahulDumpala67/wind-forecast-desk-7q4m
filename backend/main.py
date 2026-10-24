from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

BASE = "https://data.elexon.co.uk/bmrs/api/v1"
UK = ZoneInfo("Europe/London")
UTC = ZoneInfo("UTC")
app = FastAPI(title="Wind Desk API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

async def get_json(client: httpx.AsyncClient, path: str, params: dict[str, str]):
    response = await client.get(f"{BASE}/{path}", params=params)
    response.raise_for_status()
    payload = response.json()
    return payload.get("data", payload) if isinstance(payload, dict) else payload

def parse_dt(value: Any):
    try: return datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else None
    except ValueError: return None

def num(value: Any):
    try: return float(value) if value is not None else None
    except (ValueError, TypeError): return None

@app.get("/api/health")
async def health(): return {"status": "ok", "dataSource": "Elexon BMRS"}

@app.get("/api/analysis")
async def analysis(delivery_date: date = Query(..., alias="date"), cutoff: str = "12:00"):
    if not (date(2026, 1, 1) <= delivery_date <= date(2026, 1, 31)):
        raise HTTPException(400, "Select a delivery date in January 2026.")
    try: cut = time.fromisoformat(cutoff)
    except ValueError: raise HTTPException(400, "Cutoff must be HH:MM in UK local time.")
    decision_time = datetime.combine(delivery_date - timedelta(days=1), cut, UK)
    day_start = datetime.combine(delivery_date, time.min, UK)
    day_end = day_start + timedelta(days=1)
    utc_start, utc_end = day_start.astimezone(UTC), day_end.astimezone(UTC)
    publish_from = (decision_time - timedelta(days=2)).astimezone(UTC)
    publish_to = decision_time.astimezone(UTC)
    async with httpx.AsyncClient(timeout=45, headers={"Accept": "application/json"}) as client:
        try:
            actuals = await get_json(client, "datasets/FUELHH/stream", {"settlementDateFrom": delivery_date.isoformat(), "settlementDateTo": delivery_date.isoformat(), "fuelType": "WIND"})
            forecasts = await get_json(client, "datasets/WINDFOR/stream", {"publishDateTimeFrom": publish_from.isoformat(), "publishDateTimeTo": publish_to.isoformat()})
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(502, f"Could not retrieve Elexon data: {exc}")
    actual_by_time = {}
    for row in actuals or []:
        if str(row.get("fuelType", "")).upper() != "WIND": continue
        start = parse_dt(row.get("startTime"))
        if start and utc_start <= start.astimezone(UTC) < utc_end:
            actual_by_time[start.astimezone(UTC).isoformat()] = num(row.get("generation"))
    fc_by_time = {}
    for row in forecasts or []:
        start, published, value = parse_dt(row.get("startTime")), parse_dt(row.get("publishTime")), num(row.get("generation"))
        if not start or not published or value is None: continue
        start_utc, published_utc = start.astimezone(UTC), published.astimezone(UTC)
        if not (utc_start <= start_utc < utc_end and published_utc <= decision_time.astimezone(UTC)): continue
        key = start_utc.isoformat()
        if key not in fc_by_time or published_utc > fc_by_time[key][0]: fc_by_time[key] = (published_utc, value)
    rows = []
    for i in range(48):
        start = utc_start + timedelta(minutes=30*i)
        key = start.isoformat()
        actual, selected = actual_by_time.get(key), fc_by_time.get(key)
        forecast = selected[1] if selected else None
        error = forecast - actual if forecast is not None and actual is not None else None
        local = start.astimezone(UK)
        rows.append({"startTime": start.isoformat(), "time": local.strftime("%H:%M"), "actual": actual, "forecast": forecast,
                     "publishTime": selected[0].astimezone(UK).isoformat() if selected else None, "error": error})
    paired = [r for r in rows if r["error"] is not None]
    av = [r["actual"] for r in rows if r["actual"] is not None]
    fv = [r["forecast"] for r in rows if r["forecast"] is not None]
    metrics = {"mae": sum(abs(r["error"]) for r in paired)/len(paired) if paired else None,
               "bias": sum(r["error"] for r in paired)/len(paired) if paired else None, "matchedPeriods": len(paired),
               "actualCoverage": len(av), "forecastCoverage": len(fv),
               "meanActual": sum(av)/len(av) if av else None, "meanForecast": sum(fv)/len(fv) if fv else None}
    return {"date": delivery_date.isoformat(), "cutoff": decision_time.isoformat(), "timezone": "Europe/London", "rows": rows,
            "metrics": metrics, "source": {"actuals": "Elexon BMRS FUELHH (WIND)", "forecasts": "Elexon BMRS WINDFOR"}}

