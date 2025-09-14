from __future__ import annotations

import json
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_GET
from django.utils.crypto import get_random_string

from .forms import MainForm
from . import services


def index(request):
    # default 2-year window
    start, end = services.default_date_range(2)
    initial = {
        "query": "",
        "lat": 43.6532,
        "lon": -79.3832,
        "label": "Toronto, Ontario, Canada",
        "start": start,
        "end": end,
        "parameter": "GWETPROF",
    }
    form = MainForm(initial=initial)
    return render(request, "core/index.html", {"form": form})


@require_GET
def geocode_view(request):
    q = request.GET.get("q", "").strip()
    if not q:
        return HttpResponseBadRequest("Missing q")
    try:
        lat, lon, label = services.geocode_query(q)
        return JsonResponse({"lat": lat, "lon": lon, "label": label})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=404)


@require_GET
def power_view(request):
    """
    Fetch NASA POWER and render HTMX partial with a table.
    Required params: lat, lon, start, end, parameter
    """
    try:
        lat = float(request.GET.get("lat"))
        lon = float(request.GET.get("lon"))
        start = request.GET.get("start")
        end = request.GET.get("end")
        parameter = request.GET.get("parameter")
        if not (start and end and parameter):
            return HttpResponseBadRequest("Missing parameters")
    except Exception:
        return HttpResponseBadRequest("Invalid parameters")

    try:
        df = services.fetch_power(lat, lon, start, end, f"{parameter},PRECTOTCORR,T2M,WS10M")
    except Exception as e:
        return render(
            request,
            "core/_power_table.html",
            {"error": f"POWER fetch failed: {e}", "rows": [], "columns": []},
        )

    if df.empty:
        return render(
            request,
            "core/_power_table.html",
            {"error": "No data returned.", "rows": [], "columns": []},
        )

    # Build simple table rows with aligned values to avoid dict-key access issues in templates
    columns = [c for c in df.columns if c != "date"]
    rows = []
    for d, row in df.set_index("date").iterrows():
        values = []
        for c in columns:
            v = row.get(c)
            values.append(None if services.pd.isna(v) else float(v))
        rows.append({"date": d.isoformat(), "values": values})

    ctx = {
        "error": "",
        "rows": rows,
        "columns": columns,
        "lat": lat,
        "lon": lon,
        "start": start,
        "end": end,
        "parameter": parameter,
    }
    return render(request, "core/_power_table.html", ctx)


@require_GET
def forecast_view(request):
    """
    Re-fetch POWER, build series, run Prophet, and render HTMX partial with Chart.js.
    Required params: lat, lon, start, end, parameter
    Optional: horizon (default 30)
    """
    try:
        lat = float(request.GET.get("lat"))
        lon = float(request.GET.get("lon"))
        start = request.GET.get("start")
        end = request.GET.get("end")
        parameter = request.GET.get("parameter")
        horizon = int(request.GET.get("horizon", "30"))
        if not (start and end and parameter):
            return HttpResponseBadRequest("Missing parameters")
    except Exception:
        return HttpResponseBadRequest("Invalid parameters")

    # Fetch POWER
    try:
        df = services.fetch_power(lat, lon, start, end, f"{parameter},PRECTOTCORR,T2M,WS10M")
    except Exception as e:
        return render(
            request,
            "core/_forecast_chart.html",
            {"error": f"POWER fetch failed: {e}", "chart_id": get_random_string(8)},
        )

    # Build series and run Prophet with robust error handling
    try:
        series = services.build_series(df, parameter)
        forecast_points = services.make_forecast(series, horizon_days=horizon)
    except Exception as e:
        return render(
            request,
            "core/_forecast_chart.html",
            {"error": f"Forecast failed: {e}", "chart_id": get_random_string(8)},
        )

    if not forecast_points:
        # Either insufficient points (<20) or model returned empty
        return render(
            request,
            "core/_forecast_chart.html",
            {"error": "Not enough data to fit a forecast.", "chart_id": get_random_string(8)},
        )

    merged = services.merge_history_and_forecast(df, parameter, forecast_points)
    chart_id = f"chart_{get_random_string(8)}"

    return render(
        request,
        "core/_forecast_chart.html",
        {
            "error": "",
            "chart_id": chart_id,
            "parameter": parameter,
            # Use a JSON script tag in the fragment; app.js will read and render
            "points_json": json.dumps(merged),
        },
    )
