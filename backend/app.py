import logging

# pyrefly: ignore [missing-import]
from flask import Flask, jsonify, request
# pyrefly: ignore [missing-import]
from flask_cors import CORS

# pyrefly: ignore [missing-import]
from config import AREA_CENTER, AREA_RADIUS_M
# pyrefly: ignore [missing-import]
from graph_loader import GRAPH, nearest_node
# pyrefly: ignore [missing-import]
from astar import astar
from ga import genetic_algorithm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Rough degree delta for bounding-box validation (generous to avoid false rejects at edges).
_LAT_DELTA = AREA_RADIUS_M / 111_000
_LON_DELTA = AREA_RADIUS_M / (111_000 * abs(__import__("math").cos(__import__("math").radians(AREA_CENTER[0]))))


def _coords_in_area(lat, lon):
    return (
        abs(lat - AREA_CENTER[0]) <= _LAT_DELTA
        and abs(lon - AREA_CENTER[1]) <= _LON_DELTA
    )


@app.get("/api/graph-info")
def graph_info():
    return jsonify({
        "center": list(AREA_CENTER),
        "radius_m": AREA_RADIUS_M,
        "node_count": GRAPH.number_of_nodes(),
        "edge_count": GRAPH.number_of_edges(),
    })


@app.post("/api/route")
def route():
    body = request.get_json(silent=True) or {}
    start = body.get("start")
    end = body.get("end")
    algorithm = body.get("algorithm", "astar")

    if not (isinstance(start, list) and len(start) == 2 and isinstance(end, list) and len(end) == 2):
        return jsonify({"error": "Coordinates outside supported area."}), 400

    start_lat, start_lon = float(start[0]), float(start[1])
    end_lat, end_lon = float(end[0]), float(end[1])

    if not (_coords_in_area(start_lat, start_lon) and _coords_in_area(end_lat, end_lon)):
        return jsonify({"error": "Coordinates outside supported area."}), 400

    start_node = nearest_node(GRAPH, start_lat, start_lon)
    end_node = nearest_node(GRAPH, end_lat, end_lon)

    logger.info("Route request: start_node=%s end_node=%s", start_node, end_node)

    try:
        if algorithm == "ga":
            result = genetic_algorithm(GRAPH, start_node, end_node, pop_size=10, generations=20)
        else:
            result = astar(GRAPH, start_node, end_node)
    except ValueError:
        return jsonify({"error": "No path found between the selected points."}), 404

    return jsonify({
        "path": result["path_coords"],
        "distance_m": result["distance_m"],
        "nodes_explored": result["nodes_explored"],
        "explored_coords": result["explored_coords"],
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
