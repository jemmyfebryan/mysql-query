let editor;

window.onload = () => {
  editor = CodeMirror(document.getElementById("editor"), {
    mode: "text/x-sql",
    theme: "default",
    lineNumbers: true,
    value: "SELECT * FROM your_table_name;",
  });
};

function toggleTheme() {
  document.documentElement.classList.toggle("dark");
}

function getEndpoint() {
  return document.getElementById("endpoint").value || "/query";
}

async function runQuery() {
  const query = editor.getValue();
  const errorBox = document.getElementById("error");
  const resultsBox = document.getElementById("results");
  const endpoint = getEndpoint();

  errorBox.textContent = "Loading...";
  resultsBox.innerHTML = "";

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    const data = await response.json();

    if (!response.ok) throw new Error(data.detail || response.statusText);

    if (!data.rows.length) {
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
