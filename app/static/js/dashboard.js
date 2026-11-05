/* Dashboard chart. The page works without this script: the data table and the
 * summary cards are rendered by the server.
 *
 * States shown in [data-chart-state]:
 *   loading  - before the series arrives (set in the HTML)
 *   empty    - the series has no points
 *   error    - the series could not be loaded
 * The chart redraws when the colour theme changes.
 */
(function () {
  "use strict";

  var wrap = document.querySelector("[data-chart]");
  if (!wrap) {
    return;
  }

  var endpoint = wrap.getAttribute("data-endpoint");
  var canvas = wrap.querySelector("canvas");
  var stateEl = wrap.querySelector("[data-chart-state]");
  var chart = null;
  var payload = null;

  function setState(message) {
    stateEl.textContent = message || "";
    stateEl.hidden = !message;
  }

  function cssVar(name, fallback) {
    var value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
  }

  function reducedMotion() {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  function render() {
    if (typeof Chart === "undefined" || !payload) {
      return;
    }
    if (chart) {
      chart.destroy();
      chart = null;
    }

    var labels = payload.points.map(function (p) {
      return p.period.slice(0, 7);
    });
    var values = payload.points.map(function (p) {
      return p.value; // null marks a missing observation; the line breaks there
    });

    var ink = cssVar("--dp-color-ink", "#222");
    var muted = cssVar("--dp-color-ink-muted", "#555");
    var line = cssVar("--dp-color-line", "#ccc");
    var value = cssVar("--dp-color-value", "#b8860b");

    chart = new Chart(canvas, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: payload.name + " (" + payload.unit + ")",
            data: values,
            borderColor: value,
            backgroundColor: value,
            borderWidth: 2,
            pointRadius: payload.points.length > 60 ? 0 : 2,
            spanGaps: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: reducedMotion() ? false : { duration: 300 },
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                return context.dataset.label + ": " + (context.parsed.y === null ? "missing" : context.parsed.y);
              },
            },
          },
        },
        scales: {
          x: { ticks: { color: muted, maxTicksLimit: 8 }, grid: { color: line } },
          y: { ticks: { color: muted }, grid: { color: line }, title: { display: true, text: payload.unit, color: muted } },
        },
        color: ink,
      },
    });
  }

  function load() {
    setState("Loading chart…");
    fetch(endpoint, { headers: { Accept: "application/json" }, credentials: "same-origin" })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }
        return response.json();
      })
      .then(function (data) {
        payload = data;
        if (!data.points || data.points.length === 0) {
          setState("No values are stored for this range yet.");
          return;
        }
        setState("");
        render();
      })
      .catch(function () {
        setState("The chart could not be loaded. The data table below still shows the stored values.");
      });
  }

  if (typeof Chart === "undefined") {
    // The chart library did not load (for example, offline). Keep the table as the fallback.
    setState("The chart library could not be loaded. The data table below still shows the stored values.");
    return;
  }

  document.addEventListener("themechange", render);
  load();
})();
