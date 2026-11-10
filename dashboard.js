// Every log field is attacker-controlled: build cells with textContent, never innerHTML.

const COLUMN_COUNT = 7;

function cell(text, className) {
    const td = document.createElement('td');
    td.textContent = text;
    if (className) td.className = className;
    return td;
}

function showMessage(tbody, text) {
    const td = cell(text, 'message');
    td.colSpan = COLUMN_COUNT;
    const row = document.createElement('tr');
    row.appendChild(td);
    tbody.replaceChildren(row);
}

function display(value, fallback) {
    return value === undefined || value === null || value === '' ? fallback : String(value);
}

async function fetchLogs() {
    try {
        const response = await fetch('/api/telemetry');
        const logs = await response.json();
        const tbody = document.getElementById('log-body');

        if (!Array.isArray(logs) || logs.length === 0) {
            showMessage(tbody, 'No active threats detected. Radar silent.');
            return;
        }

        // The API already returns newest first
        const rows = logs.map(log => {
            const row = document.createElement('tr');

            const date = new Date(log.timestamp).toLocaleString();
            const botType = display(log.inferred_type, 'Unknown Scanner');
            const isAi = !botType.includes('Scanner');

            const payload = display(log.payload, 'None');
            const payloadSnippet = payload.length > 40 ? payload.substring(0, 40) + '...' : payload;

            row.append(
                cell(date),
                cell(display(log.source_ip, 'N/A'), 'ip'),
                cell(display(log.geo, 'Pending')),
                cell(display(log.isp, 'Pending')),
                cell(`${display(log.method, '?')} ${display(log.endpoint, '')}`, 'endpoint'),
                cell(botType, isAi ? 'alert' : ''),
                cell(payloadSnippet, 'payload'),
            );
            return row;
        });
        tbody.replaceChildren(...rows);
    } catch (e) {
        console.error('Telemetry Fetch Error:', e);
    }
}

document.getElementById('refresh').addEventListener('click', fetchLogs);

// Auto-refresh every 10 seconds
setInterval(fetchLogs, 10000);
fetchLogs();
