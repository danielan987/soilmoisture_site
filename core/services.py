# core/services.py
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Any, List, Tuple, Optional
import re

import requests
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from prophet import Prophet


# ----------------------------
# NASA POWER helpers
# ----------------------------
def power_url(lat: float, lon: float, start: str, end: str, parameters: str) -> str:
    """
    Build the NASA POWER daily point API URL.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        start: Start date in YYYYMMDD.
        end: End date in YYYYMMDD.
        parameters: Comma-separated POWER parameter list (e.g., "GWETPROF,PRECTOTCORR,T2M,WS10M").

    Returns:
        Fully composed URL string.
    """
    return (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters={parameters}&community=ag&longitude={lon}&latitude={lat}"
        f"&start={start}&end={end}&format=JSON"
    )


def parse_power(json_obj: Dict[str, Any]) -> pd.DataFrame:
    """
    Convert POWER JSON payload into a daily DataFrame with 'date' + parameter columns.

    The API returns:
      properties.parameter.{PARAM} -> {"YYYYMMDD": value}

    Returns:
        DataFrame with columns: date (datetime.date), and one column per parameter.
    """
    props = json_obj.get("properties", {})
    param_map = props.get("parameter", {})
    frames: List[pd.DataFrame] = []

    for param, series in param_map.items():
        if not isinstance(series, dict):
            continue
        df = (
            pd.Series(series, name=param)
            .rename_axis("yyyymmdd")
            .to_frame()
            .reset_index()
        )
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
    """
    Fetch POWER data and parse into a DataFrame.

    Raises:
        requests.HTTPError on non-200 responses.
    """
    url = power_url(lat, lon, start, end, parameters)
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    df = parse_power(r.json())
    return df


def build_series(df: pd.DataFrame, parameter: str) -> List[Dict[str, Any]]:
    """
    Build a Prophet-ready series from a DataFrame for the selected parameter.

    Returns:
        [{"date": "YYYY-MM-DD", "value": float}, ...]
    """
    if df.empty or parameter not in df.columns:
        return []
    series: List[Dict[str, Any]] = []
    for d, row in df.set_index("date").iterrows():
        val = row.get(parameter, None)
        if pd.isna(val):
            continue
        try:
            series.append({"date": d.isoformat(), "value": float(val)})
        except Exception:
            # Skip values that cannot be cast to float
            continue
    return series


# ----------------------------
# Forecasting
# ----------------------------
def make_forecast(series: List[Dict[str, Any]], horizon_days: int = 30,
                  daily_seasonality: bool = True,
                  weekly_seasonality: bool = True,
                  yearly_seasonality: bool = True) -> List[Dict[str, Any]]:
    """
    Fit Prophet on the input series and return history + forecast.

    Args:
        series: [{"date": "YYYY-MM-DD", "value": float}, ...] (>= 20 points recommended)
        horizon_days: Number of future days to forecast.
        *_seasonality: Prophet seasonality flags.

    Returns:
        [{"date": "YYYY-MM-DD", "yhat": float, "yhat_lower": float, "yhat_upper": float}, ...]
        Includes both history and future dates to simplify charting.
        Returns [] if not enough points to fit a model.
    """
    if len(series) < 20:
        return []

    df = pd.DataFrame([{"ds": s["date"], "y": s["value"]} for s in series])
    df["ds"] = pd.to_datetime(df["ds"])
    df = df.dropna(subset=["y"]).sort_values("ds")

    if df.empty:
        return []

    m = Prophet(
        daily_seasonality=daily_seasonality,
        weekly_seasonality=weekly_seasonality,
        yearly_seasonality=yearly_seasonality,
    )
    m.fit(df)

    future = m.make_future_dataframe(periods=int(horizon_days), freq="D", include_history=True)
    fcst = m.predict(future)
    out = fcst[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    out["ds"] = out["ds"].dt.date

    result: List[Dict[str, Any]] = []
    for d, r in out.set_index("ds").iterrows():
        result.append(
            {
                "date": d.isoformat(),
                "yhat": float(r["yhat"]),
                "yhat_lower": float(r["yhat_lower"]),
                "yhat_upper": float(r["yhat_upper"]),
            }
        )
    return result


# ----------------------------
# Geocoding
# ----------------------------
def geocode_query(query: str) -> Tuple[float, float, str]:
    """
    Geocode a free-text query or a raw 'lat,lon' string.

    Returns:
        (lat, lon, display_label)

    Raises:
        ValueError if no result.
    """
    # Try raw "lat,lon"
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$", query or "")
    if m:
        lat = float(m.group(1))
        lon = float(m.group(2))
        return lat, lon, f"{lat:.6f}, {lon:.6f}"

    geolocator = Nominatim(user_agent="soil_moisture_django")
    loc = geolocator.geocode(query, addressdetails=True, language="en")
    if not loc:
        raise ValueError("Location not found")
    return float(loc.latitude), float(loc.longitude), loc.address


def reverse_geocode(lat: float, lon: float) -> str:
    """
    Reverse geocode coordinates into a display label.

    Returns:
        address string (best-effort). Falls back to "lat, lon" if none.
    """
    geolocator = Nominatim(user_agent="soil_moisture_django")
    loc = geolocator.reverse((lat, lon), language="en", addressdetails=True)
    return loc.address if loc else f"{lat:.6f}, {lon:.6f}"


# ----------------------------
# Utilities
# ----------------------------
def default_date_range(years_back: int = 2) -> Tuple[str, str]:
    """
    Default POWER date range (today and N years back) in YYYYMMDD format.
    """
    today = date.today()
    start = date(today.year - years_back, today.month, today.day)
    return start.strftime("%Y%m%d"), today.strftime("%Y%m%d")


def merge_history_and_forecast(
    df: pd.DataFrame,
    parameter: str,
    forecast: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Merge historical values and forecast by date for charting.

    Args:
        df: POWER dataframe with 'date' and parameter column.
        parameter: e.g., "GWETPROF".
        forecast: output of make_forecast().

    Returns:
        List of dicts like:
          {
            "date": "YYYY-MM-DD",
            "hist": <float or None>,
            "yhat": <float or None>,
            "yhat_lower": <float or None>,
            "yhat_upper": <float or None>,
          }
    """
    hist_map: Dict[str, Dict[str, Any]] = {}
    if not df.empty and parameter in df.columns:
        for d, row in df.set_index("date").iterrows():
            v = row.get(parameter, None)
            hist_map[d.isoformat()] = {
                "date": d.isoformat(),
                "hist": (None if pd.isna(v) else float(v)),
            }

    for f in forecast or []:
        key = f["date"]
        if key not in hist_map:
            hist_map[key] = {"date": key, "hist": None}
        hist_map[key].update(
            {
                "yhat": float(f["yhat"]),
                "yhat_lower": float(f["yhat_lower"]),
                "yhat_upper": float(f["yhat_upper"]),
            }
        )

    merged = list(hist_map.values())
    merged.sort(key=lambda x: x["date"])
    return merged
