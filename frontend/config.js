// Loaded as a classic script before any module, so every page knows where the API lives.
// Production API: the Render service (no trailing slash). Local development uses http://127.0.0.1:8000.
(function () {
  var local = ["localhost", "127.0.0.1"].indexOf(location.hostname) !== -1;
  window.ROOMORA_CONFIG = {
    apiBase: local ? "http://127.0.0.1:8000" : "https://roomora-api-g18n.onrender.com",
  };
  window.ROOMORA_API = window.ROOMORA_CONFIG.apiBase; // read by the floating AI editor
})();
