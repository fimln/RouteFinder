import pickle
import logging
import os

# pyrefly: ignore [missing-import]
import osmnx

# pyrefly: ignore [missing-import]
from config import AREA_CENTER, AREA_RADIUS_M, NETWORK_TYPE, GRAPH_CACHE_PATH

logger = logging.getLogger(__name__)


def load_graph():
    if os.path.exists(GRAPH_CACHE_PATH):
        logger.info("Loading graph from cache: %s", GRAPH_CACHE_PATH)
        with open(GRAPH_CACHE_PATH, "rb") as f:
            return pickle.load(f)

    print(f"Downloading OSM graph for center={AREA_CENTER}, radius={AREA_RADIUS_M}m ...")
    graph = osmnx.graph_from_point(AREA_CENTER, dist=AREA_RADIUS_M, network_type=NETWORK_TYPE)
    with open(GRAPH_CACHE_PATH, "wb") as f:
        pickle.dump(graph, f)
    print("Graph downloaded and cached.")
    return graph


def nearest_node(graph, lat, lon):
    # osmnx.distance.nearest_nodes expects X=longitude, Y=latitude
    return osmnx.distance.nearest_nodes(graph, X=lon, Y=lat)


# Load once at import time; subsequent imports reuse the same object.
GRAPH = load_graph()
