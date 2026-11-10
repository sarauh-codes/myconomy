/* Progressive enhancement only. Every page works without this script. */
(function () {
  "use strict";

  var STORAGE_KEY = "myconomy-theme";
  var root = document.documentElement;

  // Busy state: a submitted form says it is working and cannot be submitted twice.
  // The server still checks everything, so this only improves feedback.
  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!(form instanceof HTMLFormElement) || form.getAttribute("aria-busy") === "true") {
      return;
    }
    if (form.checkValidity && !form.checkValidity()) {
      return; // let the browser show its own validation message
    }
    form.setAttribute("aria-busy", "true");
    form.querySelectorAll("button[type='submit']").forEach(function (button) {
      button.disabled = true;
      button.dataset.label = button.textContent;
      button.textContent = "Working…";
    });
  });

  // Move focus to the main region after the skip link is used,
  // so keyboard users continue from the right place.
  var skip = document.querySelector('a.skip-link[href="#main"]');
  if (skip) {
    skip.addEventListener("click", function () {
      var main = document.getElementById("main");
      if (main) {
        main.focus();
      }
    });
  }

  // Theme choice. The stored value is a per-browser convenience only.
  // Without a stored choice, the page follows the system preference via CSS.
  function readStoredTheme() {
    try {
      var value = window.localStorage.getItem(STORAGE_KEY);
      return value === "light" || value === "dark" ? value : null;
    } catch (err) {
      return null; // storage can be blocked; fall back to the system preference
    }
  }

  function storeTheme(value) {
    try {
      window.localStorage.setItem(STORAGE_KEY, value);
    } catch (err) {
      // Ignore: the choice still applies for this page view.
    }
  }

  function effectiveTheme() {
    var explicit = root.getAttribute("data-theme");
    if (explicit === "light" || explicit === "dark") {
      return explicit;
    }
    var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    return prefersDark ? "dark" : "light";
  }

  function applyTheme(value) {
    root.setAttribute("data-theme", value);
    // Let components such as charts re-read colours from the stylesheet.
    document.dispatchEvent(new Event("themechange"));
  }

  var toggle = document.querySelector("[data-theme-toggle]");
  if (!toggle) {
    return;
  }

  var stored = readStoredTheme();
  if (stored) {
    applyTheme(stored);
  }

  function updateToggle() {
    var next = effectiveTheme() === "dark" ? "light" : "dark";
    toggle.textContent = next === "light" ? "Light mode" : "Dark mode";
    toggle.setAttribute("aria-label", "Switch to " + next + " mode");
  }

  toggle.addEventListener("click", function () {
    var next = effectiveTheme() === "dark" ? "light" : "dark";
    applyTheme(next);
    storeTheme(next);
    updateToggle();
  });

  // Keep the label correct if the system preference changes while the page is open.
  if (window.matchMedia) {
    var query = window.matchMedia("(prefers-color-scheme: dark)");
    var onChange = function () {
      if (!readStoredTheme()) {
        updateToggle();
      }
    };
    if (query.addEventListener) {
      query.addEventListener("change", onChange);
    }
  }

  updateToggle();
  toggle.hidden = false;
})();
