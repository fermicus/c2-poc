let selectedBeaconUuid = null;
let prevDoneTaskIds    = new Set();

// Beacon table

async function loadBeacons() {
  const data  = await apiFetch("/api/ui/beacons");
  const tbody = document.getElementById("beacon-tbody");
  if (!tbody) return;

  tbody.innerHTML = "";
  data.beacons.forEach(b => {
    const isAlive = b.status === "alive";
    const dot     = isAlive
      ? '<span class="dot-alive">●</span>'
      : '<span class="dot-dead">○</span>';
    const name = b.nickname || b.hostname;
    const tag  = isAlive
      ? '<span class="tag tag-alive">ALIVE</span>'
      : '<span class="tag tag-dead">DEAD</span>';

    const tr = document.createElement("tr");
    tr.dataset.uuid = b.uuid;
    if (b.uuid === selectedBeaconUuid) tr.classList.add("selected");
    tr.innerHTML = `
      <td>${dot}</td>
      <td>${escHtml(name)}</td>
      <td style="color:var(--text-dim)">${b.uuid.slice(0, 8)}</td>
      <td>${escHtml(b.username)}@${escHtml(b.hostname)}</td>
      <td style="color:var(--text-dim)">${escHtml(b.os)}</td>
      <td>${b.sleep}s ±${b.jitter}s</td>
      <td>${tag}</td>
      <td style="color:var(--text-dim)">${tsFormat(b.last_seen)}</td>
    `;
    tr.addEventListener("click", () => selectBeacon(b));
    tbody.appendChild(tr);
  });
}

function selectBeacon(b) {
  selectedBeaconUuid = b.uuid;

  document.querySelectorAll("#beacon-tbody tr").forEach(r => {
    r.classList.toggle("selected", r.dataset.uuid === b.uuid);
  });

  const panel = document.getElementById("beacon-detail");
  if (panel) panel.style.display = "block";

  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set("detail-uuid",  b.uuid);
  set("detail-host",  b.hostname);
  set("detail-user",  b.username);
  set("detail-os",    `${b.os} (${b.arch})`);
  set("detail-pid",   b.pid);
  set("detail-sleep", `${b.sleep}s ±${b.jitter}s`);
  set("detail-first", tsFormat(b.first_seen));
  set("detail-last",  tsFormat(b.last_seen));

  const nameInput = document.getElementById("detail-name-input");
  if (nameInput) nameInput.value = b.nickname || "";

  loadTaskQueue(b.uuid);
}

// Task queue

async function loadTaskQueue(uuid) {
  const data  = await apiFetch(`/api/ui/tasks?beacon=${uuid}`);
  const tbody = document.getElementById("task-tbody");
  if (!tbody) return;

  const currentDoneIds = new Set(
    data.tasks.filter(t => t.status === "done").map(t => t.task_id)
  );
  const newDone = [...currentDoneIds].filter(id => !prevDoneTaskIds.has(id));
  prevDoneTaskIds = currentDoneIds;

  tbody.innerHTML = "";
  data.tasks.forEach(t => {
    const cmd = t.payload?.cmd || "?";
    const tr  = document.createElement("tr");
    tr.dataset.taskId = t.task_id;
    if (newDone.includes(t.task_id)) tr.classList.add("flash-done");
    tr.innerHTML = `
      <td style="color:var(--text-dim)">${t.task_id}</td>
      <td>${escHtml(cmd)}</td>
      <td class="status-${t.status}">${t.status}</td>
      <td style="color:var(--text-dim)">${tsFormat(t.created_at)}</td>
    `;
    tr.addEventListener("click", () => loadTaskResult(t.task_id));
    tbody.appendChild(tr);
  });
}

async function loadTaskResult(taskId) {
  const data = await apiFetch(`/api/ui/result?task_id=${taskId}`);
  const box  = document.getElementById("task-output");
  if (!box) return;

  if (data.result) {
    const r         = data.result;
    const exitColor = r.exit_code === 0 ? "var(--green)" : "var(--red)";
    box.innerHTML   =
      `<div class="out-header">── task ${r.task_id}  exit=<span style="color:${exitColor}">${r.exit_code}</span>  (${r.exec_time_ms}ms) ──</div>` +
      escHtml(r.stdout || "") +
      (r.stderr ? "\n── stderr ──\n" + escHtml(r.stderr) : "");
  } else {
    box.textContent = "No result yet for this task.";
  }
}

// Rename beacon

async function renameBeacon() {
  if (!selectedBeaconUuid) return;
  const name = document.getElementById("detail-name-input")?.value.trim();
  const data = await apiFetch("/api/ui/rename", {
    method: "POST",
    body: JSON.stringify({ uuid: selectedBeaconUuid, nickname: name }),
  });
  if (data.status === "ok") {
    showAlert("beacon-alert", "success", `Nickname saved.`);
    loadBeacons();
  } else {
    showAlert("beacon-alert", "error", data.message || "Failed to rename.");
  }
}
