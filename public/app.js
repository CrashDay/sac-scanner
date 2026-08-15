const body = document.querySelector("#resultsBody");
const feedDot = document.querySelector("#feedDot");
const feedText = document.querySelector("#feedText");
const refreshButton = document.querySelector("#refreshButton");

const controls = {
  account_size: document.querySelector("#accountSize"),
  risk_per_trade: document.querySelector("#riskPerTrade"),
  reward_target: document.querySelector("#rewardTarget"),
  daily_max_loss: document.querySelector("#dailyMaxLoss"),
};

refreshButton.addEventListener("click", refresh);
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
    const response = await fetch(`/api/scan?${params.toString()}`, { cache: "no-store" });
    const payload = await response.json();
    if (!payload.ok) {
      if (payload.needs_auth) {
        throw new Error("Schwab authorization needs to be refreshed before live quotes can load.");
      }
      throw new Error(payload.error || "Live scan failed");
    }
    render(payload);
    setStatus("live", "Live");
  } catch (error) {
    body.innerHTML = `<tr><td colspan="9" class="empty">${escapeHtml(error.message)}</td></tr>`;
    setStatus("error", "Offline");
  }
}

function render(payload) {
  const results = payload.results || [];
  document.querySelector("#aCount").textContent = results.filter((item) => item.grade === "A").length;
  document.querySelector("#watchCount").textContent = results.filter((item) => item.grade === "B" || item.grade === "C").length;
  document.querySelector("#rejectCount").textContent = results.filter((item) => item.grade === "Reject").length;
  document.querySelector("#updatedAt").textContent = new Date(payload.as_of).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  });

  if (!results.length) {
    body.innerHTML = `<tr><td colspan="9" class="empty">No symbols in the watchlist.</td></tr>`;
    return;
  }

  body.innerHTML = results.map((item) => `
    <tr>
      <td class="symbol">${escapeHtml(item.symbol)}</td>
      <td><span class="grade grade-${escapeHtml(item.grade)}">${escapeHtml(item.grade)}</span></td>
      <td>${item.score}</td>
      <td>${money(item.price)}</td>
      <td>${number(item.change_percent)}%</td>
      <td>${number(item.relative_volume)}x</td>
      <td>${number(item.float_millions)}M</td>
      <td>${shareText(item)}</td>
      <td class="why">${whyText(item)}</td>
    </tr>
  `).join("");
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

function setStatus(kind, text) {
  feedDot.className = `dot ${kind}`;
  feedText.textContent = text;
}

function money(value) {
  return Number(value || 0).toLocaleString([], { style: "currency", currency: "USD" });
}

function number(value) {
  return Number(value || 0).toLocaleString([], { maximumFractionDigits: 2 });
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
