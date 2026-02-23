let editor;

window.onload = () => {
  editor = CodeMirror(document.getElementById("editor"), {
    mode: "text/x-sql",
    theme: "default",
    lineNumbers: true,
    value: "SELECT * FROM your_table_name;",
  });

  // Initialize mode indicator
  updateModeIndicator();
};

function toggleTheme() {
  document.documentElement.classList.toggle("dark");
}

function getEndpoint() {
  return document.getElementById("endpoint").value || "/query";
}

function getApiKey() {
  return document.getElementById("api_key")?.value?.trim() || "";
}

function updateModeIndicator() {
  const apiKey = getApiKey();
  const indicator = document.getElementById("mode-indicator");

  if (apiKey) {
    indicator.className = "text-sm px-3 py-2 rounded bg-yellow-800 border border-yellow-700";
    indicator.innerHTML = "🔒 Secure Mode (Full SQL Access: INSERT, UPDATE, DELETE, etc.)";
  } else {
    indicator.className = "text-sm px-3 py-2 rounded bg-green-800 border border-green-700";
    indicator.innerHTML = "🔓 Public Mode (Read-only: SELECT, SHOW, DESCRIBE, EXPLAIN)";
  }
}

async function runQuery() {
  const query = editor.getValue();
  const errorBox = document.getElementById("error");
  const resultsBox = document.getElementById("results");
  const endpoint = getEndpoint();
  const apiKey = getApiKey();

  errorBox.textContent = "Loading...";
  resultsBox.innerHTML = "";

  try {
    const requestBody = { query };
    if (apiKey) {
      requestBody.api_key = apiKey;
    }

    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    });

    const data = await response.json();

    if (!response.ok) throw new Error(data.detail || response.statusText);

    // Handle secure mode responses (INSERT/UPDATE/DELETE etc.)
    if (data.message && !data.rows) {
      errorBox.textContent = "✅ " + data.message;
      if (data.last_insert_id) {
        errorBox.textContent += ` Last Insert ID: ${data.last_insert_id}`;
      }
      return;
    }

    // Handle queries with no results
    if (!data.rows || !data.rows.length) {
      errorBox.textContent = "✅ Query executed successfully. No results.";
      return;
    }

    errorBox.textContent = "";

    const headers = Object.keys(data.rows[0]);
    const table = document.createElement("table");
    table.className = "min-w-full table-auto text-sm";

    const thead = document.createElement("thead");
    thead.innerHTML = `<tr>${headers.map(h => `<th class="border px-2 py-1 bg-gray-700">${h}</th>`).join("")}</tr>`;
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    for (const row of data.rows) {
      const tr = document.createElement("tr");
      tr.innerHTML = headers.map(h => `<td class="border px-2 py-1">${row[h] ?? ""}</td>`).join("");
      tbody.appendChild(tr);
    }

    table.appendChild(tbody);
    resultsBox.appendChild(table);

    // Save for CSV
    window._lastQueryResult = data.rows;
  } catch (err) {
    errorBox.textContent = "❌ " + err.message;
  }
}

function downloadCSV() {
  const data = window._lastQueryResult;
  if (!data || data.length === 0) return alert("No data to download.");

  const headers = Object.keys(data[0]);
  const rows = [
    headers.join(","),
    ...data.map(row => headers.map(h => JSON.stringify(row[h] ?? "")).join(",")),
  ];

  const blob = new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8;" });
  saveAs(blob, "query_results.csv");
}

// Expose functions to global scope so HTML onclick works
window.runQuery = runQuery;
window.downloadCSV = downloadCSV;
window.toggleTheme = toggleTheme;
window.updateModeIndicator = updateModeIndicator;
