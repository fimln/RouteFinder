# RouteFinder

A* pathfinding on real OpenStreetMap data, applied to the walking network around UGM Yogyakarta.

## How It Works

1. On first run, the backend downloads the OSM road graph for the configured area and caches it locally
2. The frontend lets the user place a start and end marker on the map
3. The backend runs A* on the cached graph and returns the shortest walking path as an ordered list of coordinates
4. The frontend draws the route on a Leaflet map following actual roads

## Requirements

- Python 3.9+
- A browser (no install needed for the frontend)

## Usage

### 1. Start the backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
python app.py
```

On first run, the OSM graph downloads and caches to disk (30-90 seconds). Subsequent starts load from cache in under 5 seconds.

### 2. Open the frontend

Open `frontend/index.html` directly in a browser, or serve it locally:

```bash
cd frontend
python -m http.server 8080
```

Then open `http://localhost:8080`.

### 3. Finding a route

1. Click a start point on the map (green marker)
2. Click an end point (red marker)
3. The blue route appears following real roads
4. Press **Reset** to start over

## Configuration

All parameters are in `backend/config.py`:

| Constant | Default | Description |
|---|---|---|
| `PLACE_NAME` | `"Universitas Gadjah Mada, Yogyakarta"` | OSM query string for the area |
| `NETWORK_TYPE` | `"walk"` | OSM network type passed to osmnx |
| `CACHE_PATH` | `"graph_cache.pkl"` | Path where the serialized graph is stored |

## A* Algorithm

The core is in `backend/astar.py`. Each node gets a score:

```
f = g + h
```

- **g**: actual distance traveled from the start node to the current node
- **h**: Haversine distance from the current node to the goal (straight-line lower bound)

A* always expands the node with the lowest f first, which makes it faster than Dijkstra by steering the search toward the goal.

### Why it finds the shortest path

The heuristic is admissible: Haversine measures a straight line, and no road is shorter than a straight line. So h never overestimates, and A* is guaranteed to return the optimal path.

### Data structures

| Component | Role |
|---|---|
| Open set (min-heap) | Nodes to explore, ordered by f |
| `g_score` dict | Best known cost from start to each node |
| `came_from` dict | Parent pointer for path reconstruction |

## Project Structure

```
route-finder/
├── backend/
│   ├── app.py           # Flask API
│   ├── astar.py         # A* implementation
│   ├── graph_loader.py  # OSM download and cache
│   ├── config.py        # Area and parameter config
│   └── requirements.txt
├── frontend/
│   ├── index.html       # Main page
│   ├── map.js           # Leaflet map and interaction logic
│   └── style.css
└── README.md
```

## Stack

- **Backend**: Python, Flask, osmnx, networkx
- **Frontend**: Vanilla JS, Leaflet.js
- **Map data**: OpenStreetMap (UGM area, 2 km radius)
