// Beacon dropdown

async function populateBeaconDropdown(selectId) {
  const data = await apiFetch("/api/ui/beacons");
  const sel  = document.getElementById(selectId);
  if (!sel) return;

  const current = sel.value;
  sel.innerHTML = '<option value="">-- select beacon --</option>';

  data.beacons.forEach(b => {
    const dot  = b.status === "alive" ? "●" : "○";
    const name = b.nickname || b.hostname;
    const opt  = document.createElement("option");
    opt.value       = b.uuid;
    opt.textContent = `${dot} ${name} (${b.uuid.slice(0, 8)})`;
    sel.appendChild(opt);
  });

  if (current) sel.value = current;
}

// Send command

async function sendCommand() {
  const uuid = document.getElementById("cmd-beacon-select")?.value;
  const cmd  = document.getElementById("cmd-input")?.value.trim();

  if (!uuid) { showAlert("cmd-alert", "error", "Select a beacon first."); return; }
  if (!cmd)  { showAlert("cmd-alert", "error", "Command cannot be empty."); return; }

  const data = await apiFetch("/api/ui/task", {
    method: "POST",
    body: JSON.stringify({ beacon_uuid: uuid, cmd }),
  });

  if (data.status === "ok") {
    showAlert("cmd-alert", "success", `Task queued — id: ${data.task_id}`);
    document.getElementById("cmd-input").value = "";
  } else {
    showAlert("cmd-alert", "error", data.message || "Error queuing task.");
  }
}

// Presets

async function loadPresets() {
  const data = await apiFetch("/api/ui/presets");
  const grid = document.getElementById("presets-grid");
  if (!grid) return;

  grid.innerHTML = "";
  if (!data.presets.length) {
    grid.innerHTML = '<p class="empty">No presets yet. Add one below.</p>';
    return;
  }

  data.presets.forEach(p => {
    const card = document.createElement("div");
    card.className = "preset-card";
    card.innerHTML = `
      <div class="preset-name">${escHtml(p.name)}</div>
      <div class="preset-cmd">${escHtml(p.command)}</div>
      <div class="preset-actions">
        <button class="btn btn-ghost btn-sm" onclick="usePreset('${escHtml(p.command)}')">Use</button>
        <button class="btn btn-danger" onclick="deletePreset(${p.id})">
          <img src="/static/assets/icons/cross.svg" class="btn-icon btn-icon-only" />
        </button>
      </div>
    `;
    grid.appendChild(card);
  });
}

function usePreset(cmd) {
  const input = document.getElementById("cmd-input");
  if (input) { input.value = cmd; input.focus(); }
}

async function addPreset() {
  const name = document.getElementById("preset-name-input")?.value.trim();
  const cmd  = document.getElementById("preset-cmd-input")?.value.trim();

  if (!name || !cmd) { showAlert("preset-alert", "error", "Name and command required."); return; }

  const data = await apiFetch("/api/ui/presets", {
    method: "POST",
    body: JSON.stringify({ name, command: cmd }),
  });

  if (data.status === "ok") {
    document.getElementById("preset-name-input").value = "";
    document.getElementById("preset-cmd-input").value  = "";
    showAlert("preset-alert", "success", "Preset saved.");
    loadPresets();
  } else {
    showAlert("preset-alert", "error", data.message || "Failed to save preset.");
  }
}

async function deletePreset(id) {
  await apiFetch(`/api/ui/presets/${id}`, { method: "DELETE" });
  loadPresets();
}

// Init

async function loadCommandsPage() {
  await populateBeaconDropdown("cmd-beacon-select");
  await loadPresets();
}

document.addEventListener("DOMContentLoaded", () => {
  const cmdInput = document.getElementById("cmd-input");
  if (cmdInput) cmdInput.addEventListener("keydown", e => {
    if (e.key === "Enter") sendCommand();
  });
});
