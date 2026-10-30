// Loaded as a classic script before any module, so every page knows where the API lives.
// Production: replace the Render URL below with your real backend URL (no trailing slash).
(function () {
  var local = ["localhost", "127.0.0.1"].indexOf(location.hostname) !== -1;
  window.ROOMORA_CONFIG = {
    apiBase: local ? "http://127.0.0.1:8000" : "https://REPLACE-WITH-RENDER-URL",
  };
  window.ROOMORA_API = window.ROOMORA_CONFIG.apiBase; // read by the floating AI editor
})();
