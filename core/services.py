from __future__ import annotations

from datetime import date
from typing import Dict, Any, List, Tuple, Optional
import re
import requests
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim

# ---------- POWER ----------
def power_url(lat: float, lon: float, start: str, end: str, parameters: str) -> str:
    return (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters={parameters}&community=ag&longitude={lon}&latitude={lat}"
        f"&start={start}&end={end}&format=JSON"
    )

def parse_power(json_obj: Dict[str, Any]) -> pd.DataFrame:
    props = json_obj.get("properties", {})
    param_map = props.get("parameter", {})
    frames: List[pd.DataFrame] = []
    for param, series in param_map.items():
        if not isinstance(series, dict):
            continue
        df = (pd.Series(series, name=param).rename_axis("yyyymmdd").to_frame().reset_index())
        df["date"] = pd.to_datetime(df["yyyymmdd"], format="%Y%m%d").dt.date
        df.drop(columns=["yyyymmdd"], inplace=True)
        frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["date"]).astype({"date": "datetime64[ns]"})
    out = frames[0]
    for df in frames[1:]:
        out = out.merge(df, on="date", how="outer")
    out.sort_values("date", inplace=True)
    return out

def fetch_power(lat: float, lon: float, start: str, end: str, parameters: str) -> pd.DataFrame:
    url = power_url(lat, lon, start, end, parameters)
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return parse_power(r.json())

def build_series(df: pd.DataFrame, parameter: str) -> List[Dict[str, Any]]:
    if df.empty or parameter not in df.columns:
        return []
    series: List[Dict[str, Any]] = []
    for d, row in df.set_index("date").iterrows():
        val = row.get(parameter, None)
        if pd.isna(val):
            continue
        series.append({"date": d.isoformat(), "value": float(val)})
    return series

# ---------- Lazy Prophet ----------
def _get_prophet():
    try:
        from prophet import Prophet
        return Prophet
    except Exception as e:
        raise RuntimeError(
            "Prophet is not available in runtime. Install it or use a build image that supports Prophet. "
            f"Original error: {e}"
        )

def make_forecast(series: List[Dict[str, Any]], horizon_days: int = 30,
                  daily_seasonality: bool = True,
                  weekly_seasonality: bool = True,
                  yearly_seasonality: bool = True) -> List[Dict[str, Any]]:
    if len(series) < 20:
        return []
    Prophet = _get_prophet()
    df = pd.DataFrame([{"ds": s["date"], "y": s["value"]} for s in series])
    df["ds"] = pd.to_datetime(df["ds"])
    df = df.dropna(subset=["y"]).sort_values("ds")
    if df.empty:
        return []
    m = Prophet(daily_seasonality=daily_seasonality,
                weekly_seasonality=weekly_seasonality,
                yearly_seasonality=yearly_seasonality)
    m.fit(df)
    future = m.make_future_dataframe(periods=int(horizon_days), freq="D", include_history=True)
    fcst = m.predict(future)
    out = fcst[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    out["ds"] = out["ds"].dt.date
    result: List[Dict[str, Any]] = []
    for d, r in out.set_index("ds").iterrows():
        result.append({
            "date": d.isoformat(),
            "yhat": float(r["yhat"]),
            "yhat_lower": float(r["yhat_lower"]),
            "yhat_upper": float(r["yhat_upper"]),
        })
    return result

# ---------- Geocoding ----------
def geocode_query(query: str) -> Tuple[float, float, str]:
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$", query or "")
    if m:
        lat = float(m.group(1)); lon = float(m.group(2))
        return lat, lon, f"{lat:.6f}, {lon:.6f}"
    geolocator = Nominatim(user_agent="soil_moisture_django")
    loc = geolocator.geocode(query, addressdetails=True, language="en")
    if not loc:
        raise ValueError("Location not found")
    return float(loc.latitude), float(loc.longitude), loc.address

def reverse_geocode(lat: float, lon: float) -> str:
    geolocator = Nominatim(user_agent="soil_moisture_django")
    loc = geolocator.reverse((lat, lon), language="en", addressdetails=True)
    return loc.address if loc else f"{lat:.6f}, {lon:.6f}"

# ---------- Utils ----------
def default_date_range(years_back: int = 2) -> Tuple[str, str]:
    today = date.today()
    start = date(today.year - years_back, today.month, today.day)
    return start.strftime("%Y%m%d"), today.strftime("%Y%m%d")

def merge_history_and_forecast(df: pd.DataFrame, parameter: str,
                               forecast: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    hist_map: Dict[str, Dict[str, Any]] = {}
    if not df.empty and parameter in df.columns:
        for d, row in df.set_index("date").iterrows():
            v = row.get(parameter, None)
            hist_map[d.isoformat()] = {"date": d.isoformat(),
                                       "hist": (None if pd.isna(v) else float(v))}
    for f in forecast or []:
        key = f["date"]
        if key not in hist_map:
            hist_map[key] = {"date": key, "hist": None}
        hist_map[key].update({
            "yhat": float(f["yhat"]),
            "yhat_lower": float(f["yhat_lower"]),
            "yhat_upper": float(f["yhat_upper"]),
        })
    merged = list(hist_map.values())
    merged.sort(key=lambda x: x["date"])
    return merged
