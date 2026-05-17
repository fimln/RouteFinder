import heapq
import math


def _haversine(lat1, lon1, lat2, lon2):
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def astar(graph, start_node, end_node):
    end_lat = graph.nodes[end_node]["y"]
    end_lon = graph.nodes[end_node]["x"]

    def heuristic(node):
        lat = graph.nodes[node]["y"]
        lon = graph.nodes[node]["x"]
        return _haversine(lat, lon, end_lat, end_lon)

    g_score = {start_node: 0.0}
    came_from = {}
    counter = 0

    start_h = heuristic(start_node)
    open_set = [(start_h, counter, start_node)]

    closed = set()
    explored_order = []

    while open_set:
        current_f, _, current = heapq.heappop(open_set)

        if current in closed:
            continue
        closed.add(current)

        current_g = g_score[current]
        current_h = heuristic(current)

        explored_order.append({
            "lat": graph.nodes[current]["y"],
            "lon": graph.nodes[current]["x"],
            "f": round(current_f, 1),
            "g": round(current_g, 1),
            "h": round(current_h, 1),
        })

        if current == end_node:
            return _reconstruct(graph, came_from, current, current_g, explored_order)

        for neighbor, edge_dict in graph[current].items():
            min_length = min(data.get("length", float("inf")) for data in edge_dict.values())
            tentative_g = current_g + min_length

            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f = tentative_g + heuristic(neighbor)
                counter += 1
                heapq.heappush(open_set, (f, counter, neighbor))

    raise ValueError("No path found")


def _reconstruct(graph, came_from, end_node, total_distance, explored_order):
    path = []
    node = end_node
    while node in came_from:
        path.append(node)
        node = came_from[node]
    path.append(node)
    path.reverse()

    coords = [(graph.nodes[n]["y"], graph.nodes[n]["x"]) for n in path]

    return {
        "path_nodes": path,
        "path_coords": coords,
        "distance_m": total_distance,
        "nodes_explored": len(explored_order),
        "explored_coords": explored_order,
    }
