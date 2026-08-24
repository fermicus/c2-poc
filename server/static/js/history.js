let historyResults = [];

async function loadHistoryPage() {
  await populateBeaconDropdown("hist-beacon-select");
}

async function loadHistory() {
  const uuid  = document.getElementById("hist-beacon-select")?.value;
  if (!uuid) return;

  const data  = await apiFetch(`/api/ui/history?beacon=${uuid}`);
  historyResults = data.results || [];

  const tbody = document.getElementById("hist-tbody");
  if (!tbody) return;

  tbody.innerHTML = "";
  historyResults.forEach((r, i) => {
    let cmd = "?";
    try { cmd = JSON.parse(r.payload)?.cmd || "?"; } catch {}

    const exitCode  = r.exit_code;
    const exitColor = exitCode === 0 ? "var(--green)" : "var(--red)";

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td style="color:var(--text-dim)">${r.task_id}</td>
      <td>${escHtml(cmd)}</td>
      <td style="color:${exitColor}">${exitCode ?? "?"}</td>
      <td style="color:var(--text-dim)">${tsFormat(r.received_at)}</td>
    `;
    tr.addEventListener("click", () => showHistoryResult(i));
    tbody.appendChild(tr);
  });

  const out = document.getElementById("hist-output");
  if (out) out.textContent = "Select a task to view output.";
}

function showHistoryResult(i) {
  const r = historyResults[i];
  if (!r) return;

  let cmd = "?";
  try { cmd = JSON.parse(r.payload)?.cmd || "?"; } catch {}

  const exitColor = r.exit_code === 0 ? "var(--green)" : "var(--red)";
  const out = document.getElementById("hist-output");
  if (!out) return;

  out.innerHTML =
    `<div class="out-header">── task ${r.task_id}  cmd: ${escHtml(cmd)}  exit=<span style="color:${exitColor}">${r.exit_code ?? "?"}</span>  (${r.exec_time_ms ?? "?"}ms) ──</div>` +
    escHtml(r.stdout || "") +
    (r.stderr ? "\n── stderr ──\n" + escHtml(r.stderr) : "");

  document.querySelectorAll("#hist-tbody tr").forEach((tr, idx) => {
    tr.classList.toggle("selected", idx === i);
  });
}
