// Map + Geocoding + HTMX chart initialization
window.addEventListener("DOMContentLoaded", function () {
  // ----- Leaflet Map -----
  const mapEl = document.getElementById("map");
  if (mapEl && window.L) {
    const latInput = document.getElementById("lat");
    const lonInput = document.getElementById("lon");

    const lat0 = parseFloat(latInput.value) || 43.6532;
    const lon0 = parseFloat(lonInput.value) || -79.3832;

    const map = L.map("map").setView([lat0, lon0], 8);
    window.map = map;
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19
    }).addTo(map);

    let marker = L.marker([lat0, lon0]).addTo(map);
    map.on("click", function (e) {
      const { lat, lng } = e.latlng;
      latInput.value = lat.toFixed(6);
      lonInput.value = lng.toFixed(6);
      if (marker) marker.setLatLng([lat, lng]);
      else marker = L.marker([lat, lng]).addTo(map);
    });
  }

  // ----- Geocode Button -----
  const btnGeocode = document.getElementById("btn-geocode");
  if (btnGeocode) {
    btnGeocode.addEventListener("click", async function () {
      const q = document.getElementById("q").value.trim();
      const msgEl = document.getElementById("geocode-msg");
      if (!q) {
        msgEl.textContent = "Enter a query.";
        return;
      }
      msgEl.textContent = "Searching...";
      try {
        const r = await fetch(`/geocode/?q=${encodeURIComponent(q)}`, { headers: { "Accept": "application/json" }});
        if (!r.ok) {
          msgEl.textContent = (await r.text()) || "Geocoding failed.";
          return;
        }
        const data = await r.json();
        if (data.error) {
          msgEl.textContent = data.error;
          return;
        }
        document.getElementById("lat").value = Number(data.lat).toFixed(6);
        document.getElementById("lon").value = Number(data.lon).toFixed(6);
        document.getElementById("label").value = data.label;

        if (window.map && window.L) {
          window.map.setView([data.lat, data.lon], 8);
        }
        msgEl.textContent = "Location set.";
      } catch (e) {
        msgEl.textContent = String(e);
      }
    });
  }

  // ----- Chart rendering after HTMX swaps -----
  window.SMCharts = window.SMCharts || {};

  function renderForecastChart(container) {
    if (!container) return;

    // Find canvas and associated JSON script by id suffix
    const canvas = container.querySelector("canvas");
    if (!canvas) return;

    const dataScript = document.getElementById(`${canvas.id}_data`);
    if (!dataScript) {
      console.error("Forecast data script tag not found for", canvas.id);
      container.querySelector(".small.muted")?.remove();
      const err = document.createElement("div");
      err.className = "error";
      err.textContent = "Chart data not found.";
      container.appendChild(err);
      return;
    }

    let points = [];
    try {
      points = JSON.parse(dataScript.textContent || "[]");
    } catch (e) {
      console.error("Invalid chart JSON:", e);
      container.querySelector(".small.muted")?.remove();
      const err = document.createElement("div");
      err.className = "error";
      err.textContent = "Invalid chart data.";
      container.appendChild(err);
      return;
    }

    if (!points.length) {
      container.querySelector(".small.muted")?.remove();
      const err = document.createElement("div");
      err.className = "error";
      err.textContent = "No forecast points to display.";
      container.appendChild(err);
      return;
    }

    const labels = points.map(p => p.date);
    const hist = points.map(p => (p.hist === null || p.hist === undefined) ? null : Number(p.hist));
    const yhat = points.map(p => (p.yhat === null || p.yhat === undefined) ? null : Number(p.yhat));

    if (typeof Chart === "undefined") {
      console.error("Chart.js is not available on window.Chart");
      container.querySelector(".small.muted")?.remove();
      const err = document.createElement("div");
      err.className = "error";
      err.textContent = "Chart library not loaded.";
      container.appendChild(err);
      return;
    }

    const ctx = canvas.getContext("2d");
    const chartId = canvas.id;

    // Destroy prior chart if exists (id is unique per render)
    if (window.SMCharts[chartId]) {
      try { window.SMCharts[chartId].destroy(); } catch (_) {}
    }

    window.SMCharts[chartId] = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Historical",
            data: hist,
            spanGaps: true,
            borderWidth: 2,
            pointRadius: 0
          },
          {
            label: "Forecast (yhat)",
            data: yhat,
            spanGaps: true,
            borderWidth: 2,
            pointRadius: 0
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { ticks: { maxRotation: 0, autoSkip: true } },
          y: { beginAtZero: false }
        }
      }
    });

    // remove placeholder text if present
    container.querySelector(".small.muted")?.remove();
  }

  // Render chart whenever the forecast section gets swapped
  document.body.addEventListener("htmx:afterSwap", function (evt) {
    const tgt = evt.detail && evt.detail.target;
    if (tgt && tgt.id === "forecast-chart") {
      renderForecastChart(tgt);
    }
  });

  // If the page already contains a forecast (e.g., after back/forward), render it once
  const fc = document.getElementById("forecast-chart");
  if (fc && fc.querySelector("canvas")) {
    renderForecastChart(fc);
  }
});
