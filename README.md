# RouteFinder

Pathfinding on real OpenStreetMap data, applied to the walking network around UGM Yogyakarta. The app compares three route-search strategies (A*, a hybrid Genetic Algorithm, and a pure random-walk GA) and animates how each one explores the graph before drawing the final route.

## How It Works

1. On first run, the backend downloads the OSM walking graph for a center point plus radius and caches it to disk
2. The frontend lets the user pick an algorithm, then place a start and an end marker on the map
3. The backend runs the chosen algorithm on the cached graph and returns both the resulting path and the order in which nodes were explored
4. The frontend animates the exploration node by node, then draws the final route on a Leaflet map following actual roads

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

On first run, the OSM graph downloads and caches to disk. Subsequent starts load from cache. The Flask server runs on `http://localhost:5000`.

### 2. Open the frontend

Open `frontend/index.html` directly in a browser, or serve it locally:

```bash
cd frontend
python -m http.server 8080
```

Then open `http://localhost:8080`.

### 3. Finding a route

1. Pick an algorithm from the **Pilih Algoritma** dropdown (A*, Genetic Algorithm, or Random Walk)
2. Click a start point on the map (green marker)
3. Click an end point (red marker)
4. Watch the explored nodes animate; the route appears when exploration finishes
5. Use the **Animation Speed** slider to speed up or slow down the animation
6. Press **Reset** to start over

For A*, a score box shows the live `f = g + h` values of the current node. For the GA modes the score box is hidden, since they do not use a per-node heuristic.

## API

The backend exposes two endpoints (CORS enabled):

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/graph-info` | Returns map center, radius, and node/edge counts |
| `POST` | `/api/route` | Computes a route |

`POST /api/route` request body:

```json
{
  "start": [lat, lon],
  "end": [lat, lon],
  "algorithm": "astar"
}
```

`algorithm` is one of `astar` (default), `hybrid_ga`, or `pure_ga`. Coordinates are validated against the configured area bounding box. Response:

```json
{
  "path": [[lat, lon], ...],
  "distance_m": 1234.5,
  "nodes_explored": 87,
  "explored_coords": [{ "lat": ..., "lon": ..., "f": ..., "g": ..., "h": ... }, ...]
}
```

For the GA algorithms, `explored_coords` carry the string `"GA"` in place of `f`/`g`/`h`, since those have no per-node heuristic scores.

## Configuration

All parameters are in `backend/config.py`:

| Constant | Default | Description |
|---|---|---|
| `AREA_CENTER` | `(-7.7713, 110.3776)` | Center of the area as `(lat, lon)` (UGM) |
| `AREA_RADIUS_M` | `10000` | Radius in meters around the center to download |
| `NETWORK_TYPE` | `"walk"` | OSM network type passed to osmnx |
| `GRAPH_CACHE_PATH` | `"graph_cache.pkl"` | Path where the serialized graph is stored |

The graph is built with `osmnx.graph_from_point(AREA_CENTER, dist=AREA_RADIUS_M, network_type=NETWORK_TYPE)`.

## Algorithms

### A* (`backend/astar.py`)

The optimal baseline. Each node gets a score:

```
f = g + h
```

- **g**: actual distance traveled from the start node to the current node
- **h**: Haversine distance from the current node to the goal (straight-line lower bound)

A* always expands the node with the lowest f first, which makes it faster than Dijkstra by steering the search toward the goal. The heuristic is admissible (Haversine never overestimates, since no road is shorter than a straight line), so A* is guaranteed to return the optimal path.

Data structures:

| Component | Role |
|---|---|
| Open set (min-heap) | Nodes to explore, ordered by f |
| `g_score` dict | Best known cost from start to each node |
| `came_from` dict | Parent pointer for path reconstruction |
| `closed` set | Already-expanded nodes |

A* also records the order nodes were expanded (with their f/g/h) so the frontend can replay the search.

### Hybrid GA (`backend/gax2.py`, `hybrid_ga`)

A Genetic Algorithm seeded with valid paths. The initial population comes from running `networkx.shortest_path` on randomly perturbed edge weights (each edge length scaled by a random factor), so every individual is a connected route. Evolution then applies:

- **Selection**: tournament selection (best of 3 random individuals) plus elitism (top 2 carried over)
- **Crossover**: splice two parents at a shared node, with a fallback that searches other shared nodes if the splice would break connectivity
- **Mutation**: re-route a random suffix of the path using the same perturbed-weight shortest path

Fitness is total path distance (lower is better). Defaults: `pop_size=10`, `generations=20`.

### Pure GA / Random Walk (`backend/gax2.py`, `pure_ga`)

A baseline GA whose paths come from blind random walks (each step picks a random neighbor) capped at `max_steps=1000`. Building the initial population is expensive because most random walks never reach the goal, so it retries up to `pop_size * 50` times. Individuals that fail to reach the goal are penalized with infinite distance. This mode often fails to find a route for distant points; the API returns a 404 with a suggestion to use A* in that case.

## Project Structure

```
RouteFinder/
├── backend/
│   ├── app.py           # Flask API (graph-info + route endpoints)
│   ├── astar.py         # A* implementation
│   ├── gax2.py          # Active GA module (hybrid_ga + pure_ga)
│   ├── ga.py            # Earlier GA iteration (unused)
│   ├── gax.py           # Earlier GA iteration (unused)
│   ├── graph_loader.py  # OSM download and cache
│   ├── config.py        # Area and parameter config
│   └── requirements.txt
├── frontend/
│   ├── index.html       # Main page (map, algorithm picker, score box, legend)
│   ├── map.js           # Leaflet map, interaction, and exploration animation
│   └── style.css
├── astar_graph_simulation.html  # Standalone A* explainer/visualization
└── README.md
```

> Note: `app.py` imports only `gax2`. `ga.py` and `gax.py` are earlier iterations kept in the tree but not wired into the app.

## Stack

- **Backend**: Python, Flask, flask-cors, osmnx, networkx, numpy, scikit-learn
- **Frontend**: Vanilla JS, Leaflet.js
- **Map data**: OpenStreetMap (UGM area, 10 km radius)
