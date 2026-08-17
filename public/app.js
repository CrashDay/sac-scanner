const body = document.querySelector("#resultsBody");
const feedDot = document.querySelector("#feedDot");
const feedText = document.querySelector("#feedText");
const refreshButton = document.querySelector("#refreshButton");
const positionsBody = document.querySelector("#positionsBody");
const dayLock = document.querySelector("#dayLock");

const controls = {
  account_size: document.querySelector("#accountSize"),
  risk_per_trade: document.querySelector("#riskPerTrade"),
  reward_target: document.querySelector("#rewardTarget"),
  daily_max_loss: document.querySelector("#dailyMaxLoss"),
};

let latestResults = [];

refreshButton.addEventListener("click", refresh);
body.addEventListener("click", handleGateClick);
positionsBody.addEventListener("click", handlePositionClick);
for (const input of Object.values(controls)) {
  input.addEventListener("change", refresh);
}

refresh();
setInterval(refresh, 15000);

async function refresh() {
  setStatus("idle", "Refreshing");
  const params = new URLSearchParams();
  for (const [key, input] of Object.entries(controls)) {
    params.set(key, input.value);
  }

  try {
    const [scanResponse, dayResponse] = await Promise.all([
      fetch(`/api/scan?${params.toString()}`, { cache: "no-store" }),
      fetch(`/api/day-trader/status?${params.toString()}`, { cache: "no-store" }),
    ]);
    const dayStatus = await dayResponse.json();
    if (!dayStatus.ok) {
      throw new Error(dayStatus.error || "SAC day-trader status failed");
    }
    const payload = await scanResponse.json();
    if (!payload.ok) {
      if (payload.needs_auth) {
        throw new Error("Schwab authorization needs to be refreshed before live quotes can load.");
      }
      throw new Error(payload.error || "Live scan failed");
    }
    render(payload, dayStatus);
    setStatus("live", "Live");
  } catch (error) {
    body.innerHTML = `<tr><td colspan="10" class="empty">${escapeHtml(error.message)}</td></tr>`;
    setStatus("error", "Offline");
  }
}

function render(payload, dayStatus) {
  const results = payload.results || [];
  latestResults = results;
  document.querySelector("#aCount").textContent = results.filter((item) => item.grade === "A").length;
  document.querySelector("#watchCount").textContent = results.filter((item) => item.grade === "B" || item.grade === "C").length;
  document.querySelector("#rejectCount").textContent = results.filter((item) => item.grade === "Reject").length;
  document.querySelector("#dayPnl").textContent = signedMoney(dayStatus.realized_pnl);
  document.querySelector("#dayTrades").textContent = `${dayStatus.entry_count}/${dayStatus.config.max_trades_per_day}`;
  document.querySelector("#updatedAt").textContent = new Date(payload.as_of).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  });
  renderDayStatus(dayStatus);

  if (!results.length) {
    body.innerHTML = `<tr><td colspan="10" class="empty">No live or cached SAC candidates currently match the scanner.</td></tr>`;
    return;
  }

  body.innerHTML = results.map((item, index) => `
    <tr>
      <td class="symbol">${escapeHtml(item.symbol)}</td>
      <td><span class="grade grade-${escapeHtml(item.grade)}">${escapeHtml(item.grade)}</span></td>
      <td>${item.score}</td>
      <td>${money(item.price)}</td>
      <td>${number(item.change_percent)}%</td>
      <td>${number(item.relative_volume)}x</td>
      <td>${floatText(item)}</td>
      <td>${shareText(item)}</td>
      <td>${gateButton(item, index, dayStatus)}</td>
      <td class="why">${whyText(item)}</td>
    </tr>
  `).join("");
}

function renderDayStatus(dayStatus) {
  dayLock.textContent = dayStatus.locked ? dayStatus.lock_reason : "Manual gate";
  dayLock.className = `lockBadge ${dayStatus.locked ? "locked" : ""}`;

  const positions = dayStatus.open_positions || [];
  if (!positions.length) {
    positionsBody.textContent = "No open SAC day trade.";
    return;
  }

  positionsBody.innerHTML = positions.map((position) => `
    <div class="positionRow">
      <div>
        <strong>${escapeHtml(position.symbol)}</strong>
        <span>${position.qty} @ ${money(position.entry_price)}</span>
        <span>Stop ${money(position.stop_price)}</span>
        <span>Target ${money(position.target_price)}</span>
      </div>
      <label>Exit <input class="exitPrice" data-position-id="${escapeHtml(position.position_id)}" type="number" min="0" step="0.01" value="${Number(position.target_price || position.entry_price).toFixed(2)}" /></label>
      <button class="closePosition" data-position-id="${escapeHtml(position.position_id)}" type="button">Close</button>
    </div>
  `).join("");
}

function gateButton(item, index, dayStatus) {
  const eligible = !dayStatus.locked && (item.grade === "A" || item.grade === "B");
  const label = eligible ? "Approve" : "Watch";
  return `<button class="gateButton" data-index="${index}" type="button" ${eligible ? "" : "disabled"}>${label}</button>`;
}

async function handleGateClick(event) {
  const button = event.target.closest(".gateButton");
  if (!button || button.disabled) return;
  const candidate = latestResults[Number(button.dataset.index)];
  if (!candidate) return;
  button.disabled = true;
  button.textContent = "Approving";
  try {
    const result = await postJson("/api/day-trader/approve-entry", {
      candidate,
      risk: riskPayload(),
    });
    if (!result.ok) throw new Error(result.error || "Approval failed");
    await refresh();
  } catch (error) {
    button.textContent = "Approve";
    button.disabled = false;
    setStatus("error", error.message);
  }
}

async function handlePositionClick(event) {
  const button = event.target.closest(".closePosition");
  if (!button) return;
  const input = positionsBody.querySelector(`.exitPrice[data-position-id="${cssEscape(button.dataset.positionId)}"]`);
  const exitPrice = Number(input?.value || 0);
  button.disabled = true;
  button.textContent = "Closing";
  try {
    const result = await postJson("/api/day-trader/close-position", {
      position_id: button.dataset.positionId,
      exit_price: exitPrice,
      risk: riskPayload(),
    });
    if (!result.ok) throw new Error(result.error || "Close failed");
    await refresh();
  } catch (error) {
    button.textContent = "Close";
    button.disabled = false;
    setStatus("error", error.message);
  }
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return response.json();
}

function riskPayload() {
  return Object.fromEntries(Object.entries(controls).map(([key, input]) => [key, Number(input.value)]));
}

function whyText(item) {
  const parts = [];
  if (item.news_headline) parts.push(`<strong>${escapeHtml(item.news_headline)}</strong>`);
  parts.push(...(item.passes || []).slice(0, 3).map(escapeHtml));
  if (item.fails?.length) parts.push(`<span>Fails: ${escapeHtml(item.fails.join("; "))}</span>`);
  if (item.warnings?.length) parts.push(`<span>Watch: ${escapeHtml(item.warnings.join("; "))}</span>`);
  return parts.join("<br />");
}

function shareText(item) {
  const shares = item.max_shares_by_risk || item.max_shares_by_cash || 0;
  const target = item.target_profit_price ? `<br />Target ${money(item.target_profit_price)}` : "";
  return `${shares}${target}`;
}

function floatText(item) {
  if (item.float_source === "unknown") return "Unknown";
  const suffix = item.float_source === "schwab_shares_outstanding" ? "M est." : "M";
  return `${number(item.float_millions)}${suffix}`;
}

function setStatus(kind, text) {
  feedDot.className = `dot ${kind}`;
  feedText.textContent = text;
}

function money(value) {
  return Number(value || 0).toLocaleString([], { style: "currency", currency: "USD" });
}

function signedMoney(value) {
  const amount = Number(value || 0);
  return `${amount > 0 ? "+" : ""}${money(amount)}`;
}

function number(value) {
  return Number(value || 0).toLocaleString([], { maximumFractionDigits: 2 });
}

function cssEscape(value) {
  if (window.CSS?.escape) return CSS.escape(value);
  return String(value).replace(/["\\]/g, "\\$&");
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}
