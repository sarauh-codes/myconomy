/* Progressive enhancement only. Every page works without this script. */
(function () {
  "use strict";

  // Move focus to the main region after an in-page skip link is used,
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
})();
