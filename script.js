const form = document.getElementById("rigcheck-form");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");
const loaderEl = document.getElementById("loader");

const titleEl = document.getElementById("game-title");
const descriptionEl = document.getElementById("game-description");
const confidenceEl = document.getElementById("confidence-chip");
const confidenceFillEl = document.getElementById("confidence-fill");
const fpsEl = document.getElementById("fps-estimate");
const hardwareEl = document.getElementById("hardware-advice");
const keywordsEl = document.getElementById("keywords");
const alternativesList = document.getElementById("alternatives-list");
const steamLinkEl = document.getElementById("steam-link");
const budgetMetaEl = document.getElementById("budget-meta");
const gpuMetaEl = document.getElementById("gpu-meta");
const ramMetaEl = document.getElementById("ram-meta");

const API_CANDIDATES = [
  "http://127.0.0.1:8000/recommend",
  "http://127.0.0.1:8001/recommend",
];

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const description = document.getElementById("description").value.trim();
  const budget = Number(document.getElementById("budget").value);
  const gpuTier = Number(document.getElementById("gpu-tier").value);
  const ram = Number(document.getElementById("ram").value);

  if (!description) {
    statusEl.textContent = "Please describe the kind of game you want.";
    return;
  }

  if (!Number.isFinite(budget) || budget < 0) {
    statusEl.textContent = "Budget must be a positive number.";
    return;
  }

  if (!Number.isFinite(gpuTier) || gpuTier < 0) {
    statusEl.textContent = "GPU tier must be a positive number.";
    return;
  }

  if (!Number.isFinite(ram) || ram < 0) {
    statusEl.textContent = "RAM must be a positive number.";
    return;
  }

  setStatus("");
  loaderEl.classList.remove("hidden");
  resultEl.classList.add("hidden");

  try {
    const payload = {
      description,
      budget,
      gpu_tier: gpuTier,
      ram,
    };

    const { data, url } = await postWithFallback(payload);
    renderResult(data, url, { budget, gpuTier, ram });
  } catch (error) {
    loaderEl.classList.add("hidden");
    setStatus(`Error: ${error.message}`);
  }
});

async function postWithFallback(payload) {
  let lastError = null;

  for (const url of API_CANDIDATES) {
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));

      if (response.ok) {
        return { data, url };
      }

      if (response.status === 404) {
        lastError = new Error(data.detail || "Not Found");
        continue;
      }

      throw new Error(data.detail || "Server error");
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error("Server error");
}

function renderResult(data, url, inputs) {
  loaderEl.classList.add("hidden");

  const normalized = normalizeResponse(data);

  if (!normalized || !normalized.recommended_game) {
    setStatus(
      (normalized && (normalized.description || normalized.message)) || "No matching results."
    );
    resultEl.classList.add("hidden");
    return;
  }

  setStatus("");

  titleEl.textContent = normalized.recommended_game;
  descriptionEl.textContent = normalized.description;

  const confidence = Number(normalized.confidence) || 0;
  confidenceEl.textContent = `${confidence}%`;
  confidenceFillEl.style.width = "0%";
  requestAnimationFrame(() => {
    confidenceFillEl.style.width = `${Math.max(0, Math.min(100, confidence))}%`;
  });

  fpsEl.textContent = estimateFps(confidence);
  hardwareEl.textContent = normalized.hardware_advice || "No hardware advice returned.";

  budgetMetaEl.textContent = `INR ${inputs.budget}`;
  gpuMetaEl.textContent = String(inputs.gpuTier);
  ramMetaEl.textContent = `${inputs.ram} GB`;

  // Steam store link for recommended game
  if (normalized.store_url) {
    steamLinkEl.href = normalized.store_url;
    // Adjust label for non-Steam links (Valorant, Minecraft)
    const isSteam = normalized.store_url.includes("store.steampowered.com");
    steamLinkEl.lastChild.textContent = isSteam ? " View on Steam" : " Get the Game";
    steamLinkEl.classList.remove("hidden");
  } else {
    steamLinkEl.classList.add("hidden");
  }

  fillChips(keywordsEl, normalized.matched_keywords, "No matched keywords returned.");
  renderAlternatives(alternativesList, normalized.alternative_games);

  resultEl.classList.remove("hidden");
  applyResultAnimations(resultEl);
}

// UI-only FPS estimate derived from confidence for a lightweight, friendly cue.
function estimateFps(confidence) {
  if (confidence >= 85) {
    return "90+ FPS";
  }
  if (confidence >= 70) {
    return "60-90 FPS";
  }
  if (confidence >= 55) {
    return "45-60 FPS";
  }
  if (confidence >= 40) {
    return "30-45 FPS";
  }
  return "30 FPS cap";
}

function fillChips(container, items, emptyMessage) {
  container.innerHTML = "";

  if (!items || items.length === 0) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = emptyMessage;
    container.appendChild(chip);
    return;
  }

  items.forEach((item) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = item;
    container.appendChild(chip);
  });
}

function renderAlternatives(container, alternatives) {
  container.innerHTML = "";

  if (!alternatives || alternatives.length === 0) {
    const card = document.createElement("div");
    card.className = "alt-card";
    card.innerHTML = "<p class=\"muted\">No alternatives found.</p>";
    container.appendChild(card);
    return;
  }

  alternatives.forEach((game, index) => {
    const card = document.createElement("div");
    card.className = "alt-card";
    card.style.animationDelay = `${index * 90}ms`;

    const title = document.createElement("p");
    title.className = "alt-title";
    title.textContent = game.title || "Untitled";

    const price = document.createElement("p");
    price.className = "alt-price";
    price.textContent = game.price_inr ? `INR ${game.price_inr}` : "Price unavailable";

    card.appendChild(title);
    card.appendChild(price);

    // Steam / store link for alternatives
    if (game.store_url) {
      const isSteam = game.store_url.includes("store.steampowered.com");
      const link = document.createElement("a");
      link.className = "alt-store-link";
      link.href = game.store_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.innerHTML = `<svg class="steam-icon-sm" viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M12 2a10 10 0 0 0-9.96 9.04l5.35 2.21a2.83 2.83 0 0 1 1.6-.49c.06 0 .11 0 .17.01l2.4-3.47v-.05a3.77 3.77 0 1 1 3.77 3.77h-.09l-3.41 2.44c0 .08.01.16.01.24a2.84 2.84 0 0 1-5.66.29L2.1 14.46A10 10 0 1 0 12 2zm-5.84 14.3l-1.71-.71a2.13 2.13 0 0 0 3.87.84 2.13 2.13 0 0 0-1.03-2.83l1.77.73a1.57 1.57 0 1 1-2.9 1.97zm9.6-5.05a2.52 2.52 0 1 0-2.52-2.52 2.52 2.52 0 0 0 2.52 2.52z"/></svg> ${isSteam ? "Steam" : "Store"}`;
      card.appendChild(link);
    }

    container.appendChild(card);
  });
}

function setStatus(message) {
  if (!message) {
    statusEl.textContent = "";
    statusEl.classList.add("hidden");
    return;
  }

  statusEl.textContent = message;
  statusEl.classList.remove("hidden");
}

function normalizeResponse(data) {
  if (!data) {
    return null;
  }

  if (data.recommended_game !== undefined) {
    return data;
  }

  if (data.winner) {
    const matchedKeywords = Array.isArray(data.reasons)
      ? data.reasons.map((reason) => reason.replace("Matches your request for:", "").replace(/["']/g, "").trim())
      : [];

    return {
      recommended_game: data.winner.title || "",
      confidence: data.confidence || 0,
      description: data.winner.description || data.message || "",
      hardware_advice: data.hardware_advice || "",
      matched_keywords: matchedKeywords.filter(Boolean),
      alternative_games: Array.isArray(data.alternatives) ? data.alternatives : [],
    };
  }

  return data;
}

function applyResultAnimations(container) {
  const children = Array.from(container.children);
  children.forEach((child, index) => {
    child.style.setProperty("--delay", `${index * 80}ms`);
  });

  container.classList.remove("animate-in");
  void container.offsetWidth;
  container.classList.add("animate-in");
}
