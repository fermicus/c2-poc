async function apiFetch(url, opts = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  return res.json();
}

// Timestamp formatter
function tsFormat(unix) {
  return new Date(unix * 1000).toLocaleString("en-GB", {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
    hour12: false,
  }).replace(",", "");
}

// Alert helper
function showAlert(id, type, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = `alert alert-${type} show`;
  el.textContent = msg;
  setTimeout(() => { el.className = `alert alert-${type}`; }, 4000);
}

// HTML escape
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g,  "&lt;")
    .replace(/>/g,  "&gt;")
    .replace(/"/g,  "&quot;");
}

// Nuke
async function nukeData() {
  const confirmed = confirm(
    "This will delete the entire database — all beacons, tasks and results will be wiped. Continue?"
  );
  if (!confirmed) return;

  const data = await apiFetch("/api/ui/nuke", { method: "POST" });
  if (data.status === "ok") {
    window.location.href = "/";
  } else {
    alert("Nuke failed: " + (data.message || "unknown error"));
  }
}
