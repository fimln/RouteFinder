const API_BASE = "http://localhost:5000";

const MIN_DELAY_MS = 15;
const MAX_DELAY_MS = 400;

let map;
let state = "awaiting_start";
let startMarker = null;
let endMarker = null;
let routeLine = null;
let explorationLayer = null;
let currentHighlight = null;
let startCoords = null;
let animationTimer = null;

const statusEl       = document.getElementById("status");
const distanceEl     = document.getElementById("distance");
const nodesEl        = document.getElementById("nodes-explored");
const resetBtn       = document.getElementById("reset");
const scoreBox       = document.getElementById("score-box");
const scoreF         = document.getElementById("score-f");
const scoreG         = document.getElementById("score-g");
const scoreH         = document.getElementById("score-h");
const speedSlider    = document.getElementById("speed-slider");
const algoSelect     = document.getElementById("algo-select");

function getSpeedMultiplier() {
  const val = parseInt(speedSlider.value);
  return Math.pow(2, val - 1);
}

async function init() {
  const info = await fetch(`${API_BASE}/api/graph-info`).then(r => r.json());
  const [lat, lon] = info.center;

  map = L.map("map").setView([lat, lon], 15);

  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
  }).addTo(map);

  map.on("click", onMapClick);
}

async function onMapClick(e) {
  if (state === "done") return;

  const { lat, lng } = e.latlng;

  if (state === "awaiting_start") {
    startCoords = [lat, lng];
    startMarker = L.marker([lat, lng], { icon: greenIcon() }).addTo(map)
      .bindTooltip("Start", { permanent: true, direction: "top", offset: [0, -8] })
      .openTooltip();
    state = "awaiting_end";
    statusEl.textContent = "Klik titik tujuan";
    return;
  }

  if (state === "awaiting_end") {
    const endCoords = [lat, lng];
    endMarker = L.marker([lat, lng], { icon: redIcon() }).addTo(map)
      .bindTooltip("Goal", { permanent: true, direction: "top", offset: [0, -8] })
      .openTooltip();
    state = "done";

    const algorithm = algoSelect.value;
    statusEl.textContent = `Mencari rute dengan ${algorithm.toUpperCase()}...`;

    distanceEl.textContent = "";
    nodesEl.textContent = "";

    // pilihan scorebox 
    if (algorithm === "hybrid_ga" || algorithm === "pure_ga") {
      scoreBox.classList.add("hidden");
    } else {
      scoreBox.classList.remove("hidden");
      scoreF.textContent = "--";
      scoreG.textContent = "--";
      scoreH.textContent = "--";
    }

    try {
      const res = await fetch(`${API_BASE}/api/route`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Kirim pilihan algoritma ke server
        body: JSON.stringify({
          start: [startCoords[0], startCoords[1]],
          end: [endCoords[0], endCoords[1]],
          algorithm: algorithm
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        statusEl.textContent = data.error || "Terjadi kesalahan.";
        scoreBox.classList.add("hidden");
        return;
      }

      animateExploration(data.explored_coords, data.path, data.distance_m, data.nodes_explored);

    } catch (err) {
      statusEl.textContent = "Gagal menghubungi server.";
      scoreBox.classList.add("hidden");
    }
  }
}

function placeExploredNode(node) {
  const { lat, lon, f, g, h } = node;

  let tooltipHTML = "";
  if (f === "GA") {
    tooltipHTML = `<b>Genetic Algorithm</b><br>Menyebar & mengevaluasi<br>probabilitas kromosom rute.`;
  } else {
    tooltipHTML = `<b>f</b> = ${f} m<br><span style="color:#8bc34a;"><b>g</b> = ${g} m</span><br><span style="color:#ff9800;"><b>h</b> = ${h} m</span>`;
  }

  L.circleMarker([lat, lon], {
    radius: 7,
    color: "#bf5700",
    fillColor: "#f57c00",
    fillOpacity: 0.65,
    weight: 1.5,
    interactive: true,
    bubblingMouseEvents: false,
  }).addTo(explorationLayer)
    .bindTooltip(tooltipHTML, {
        className: "explored-tooltip",
        direction: "top",
        offset: [0, -8],
        sticky: true,
      }
    );

  if (currentHighlight) { map.removeLayer(currentHighlight); }
  currentHighlight = L.circleMarker([lat, lon], {
    radius: 10,
    color: "#f9a825",
    fillColor: "#ffeb3b",
    fillOpacity: 0.85,
    weight: 3,
    interactive: false,
    bubblingMouseEvents: false,
  }).addTo(map);

  if (f != "GA") {
    scoreF.textContent = `${f} m`;
    scoreG.textContent = `${g} m`;
    scoreH.textContent = `${h} m`;
  }
}

function animateExploration(explored, path, distanceM, nodesExplored) {
  explorationLayer = L.layerGroup().addTo(map);

  const total = explored.length;
  const speedMult = getSpeedMultiplier();
  const baseDelay = Math.min(MAX_DELAY_MS, Math.max(MIN_DELAY_MS, 200 / Math.sqrt(speedMult)));
  let i = 0;

  statusEl.textContent = `Exploring nodes: 0 / ${total}`;

  animationTimer = setInterval(() => {
    if (i >= total) {
      clearInterval(animationTimer);
      animationTimer = null;
      finishAnimation(path, distanceM, nodesExplored);
      return;
    }

    placeExploredNode(explored[i]);
    i++;
    if (i % 5 === 0 || i === total) {
      statusEl.textContent = `Exploring nodes: ${i} / ${total}`;
    }
  }, baseDelay);

  speedSlider.addEventListener("input", updateDelay);

  function updateDelay() {
    if (!animationTimer) return;
    const newDelay = Math.min(MAX_DELAY_MS, Math.max(MIN_DELAY_MS, 200 / Math.sqrt(getSpeedMultiplier())));
    clearInterval(animationTimer);
    animationTimer = setInterval(runStep, newDelay);
  }

  function runStep() {
    if (i >= total) {
      clearInterval(animationTimer);
      animationTimer = null;
      speedSlider.removeEventListener("input", updateDelay);
      finishAnimation(path, distanceM, nodesExplored);
      return;
    }

    placeExploredNode(explored[i]);
    i++;
    if (i % 5 === 0 || i === total) {
      statusEl.textContent = `Exploring nodes: ${i} / ${total}`;
    }
  }
}

function finishAnimation(path, distanceM, nodesExplored) {
  if (currentHighlight) { map.removeLayer(currentHighlight); currentHighlight = null; }
  drawResult(path, distanceM, nodesExplored);
}

function drawResult(path, distanceM, nodesExplored) {
  explorationLayer.eachLayer(function (layer) {
    layer.setStyle({ fillOpacity: 0.35, opacity: 0.4 });
    layer._path.style.pointerEvents = "auto";
  });

  const algorithm = algoSelect.value;
  const routeColor = algorithm === "ga" ? "#9c27b0" : "#1a73e8";

  routeLine = L.polyline(path, {
    color: "#1a73e8",
    weight: 5,
    interactive: false,
    bubblingMouseEvents: false,
  }).addTo(map);

  map.fitBounds(routeLine.getBounds(), { padding: [40, 40] });

  const dm = distanceM;
  distanceEl.textContent = dm >= 1000
    ? `Jarak: ${(dm / 1000).toFixed(2)} km`
    : `Jarak: ${dm.toFixed(0)} m`;

  nodesEl.textContent = `Node dieksplorasi: ${nodesExplored}`;
  statusEl.textContent = "Rute ditemukan.";
  scoreBox.classList.add("hidden");
}

resetBtn.addEventListener("click", () => {
  speedSlider.removeEventListener("input", () => {});

  if (animationTimer) {
    clearInterval(animationTimer);
    animationTimer = null;
  }

  if (startMarker)       { map.removeLayer(startMarker);      startMarker = null; }
  if (endMarker)         { map.removeLayer(endMarker);        endMarker = null; }
  if (routeLine)         { map.removeLayer(routeLine);        routeLine = null; }
  if (explorationLayer)  { map.removeLayer(explorationLayer); explorationLayer = null; }
  if (currentHighlight)  { map.removeLayer(currentHighlight); currentHighlight = null; }

  startCoords = null;
  state = "awaiting_start";
  statusEl.textContent = "Klik titik awal";
  distanceEl.textContent = "";
  nodesEl.textContent = "";

  const algorithm = algoSelect.value;
  if (algorithm === "hybrid_ga" || algorithm === "pure_ga") {
    scoreBox.classList.add("hidden");
  } else {
    scoreBox.classList.remove("hidden");
  }

  scoreF.textContent = "--";
  scoreG.textContent = "--";
  scoreH.textContent = "--";
});

// Update score box otomatis ketika ganti dropdown (tanpa perlu klik reset)
algoSelect.addEventListener("change", (e) => {
    if(state === "awaiting_start" || state === "awaiting_end"){
        if (e.target.value === "hybrid_ga" || e.target.value === "pure_ga") {
            scoreBox.classList.add("hidden");
        } else {
            scoreBox.classList.remove("hidden");
        }
    }
});

function greenIcon() {
  return L.icon({
    iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png",
    shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
    iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41],
  });
}

function redIcon() {
  return L.icon({
    iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
    shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
    iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41],
  });
}

init();
