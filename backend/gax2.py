import random
import logging
import networkx as nx

logger = logging.getLogger(__name__)

def calculate_path_distance(graph, path):
    dist = 0.0
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i+1]
        edge_data = graph.get_edge_data(u, v)
        min_len = min(d.get("length", float("inf")) for d in edge_data.values())
        dist += min_len
    return dist

def _is_valid_path(graph, path):
    """Cek setiap pasangan node consecutivos punya edge langsung di graph."""
    return all(graph.has_edge(path[i], path[i + 1]) for i in range(len(path) - 1))


def crossover(parent1, parent2, graph=None):
    common_nodes = set(parent1[1:-1]).intersection(set(parent2[1:-1]))
    if not common_nodes:
        return parent1

    crossover_point = random.choice(list(common_nodes))
    idx1 = parent1.index(crossover_point)
    idx2 = parent2.index(crossover_point)

    child = parent1[:idx1] + parent2[idx2:]

    # Anak hasil crossover belum tentu kontinyu (edge parent1[idx1-1] -> parent2[idx2]
    # bisa tidak ada). Jika graph diberikan, validasi dan kalau tidak valid coba titik
    # potong lain, kalau masih gagal kembalikan parent1 (solusi konservatif).
    if graph is not None and not _is_valid_path(graph, child):
        for candidate in list(common_nodes):
            if candidate == crossover_point:
                continue
            ci = parent1.index(candidate)
            cj = parent2.index(candidate)
            cand_child = parent1[:ci] + parent2[cj:]
            if _is_valid_path(graph, cand_child):
                return cand_child
        return parent1
    return child

# =====================================================================
# BLOK 1: HYBRID GA (GA + Dijkstra Noise) -> Ini adalah kode aslimu
# =====================================================================

def generate_hybrid_path(graph, start_node, end_node, explored_order):
    for u, v, k, data in graph.edges(keys=True, data=True):
        length = data.get("length", 10.0)
        data["temp_weight"] = length * random.uniform(1.0, 5.0)
    
    try:
        path = nx.shortest_path(graph, start_node, end_node, weight="temp_weight")
        explored_order.extend(path)
        return path
    except nx.NetworkXNoPath:
        return None

def mutate_hybrid(graph, path, end_node, explored_order):
    if len(path) <= 2:
        return path
    break_idx = random.randint(1, len(path)-2)
    break_node = path[break_idx]
    
    new_segment = generate_hybrid_path(graph, break_node, end_node, explored_order)
    if new_segment:
        return path[:break_idx] + new_segment
    return path

def hybrid_ga(graph, start_node, end_node, pop_size=10, generations=20):
    explored_order = []
    population = []

    for _ in range(pop_size):
        path = generate_hybrid_path(graph, start_node, end_node, explored_order)
        if path:
            population.append(path)

    if not population:
        return _format_result(best_dist=-1.0, best_path=[], explored_order=explored_order, graph=graph)

    best_path = None
    best_dist = float('inf')

    for gen in range(generations):
        pop_fitness = []
        for path in population:
            dist = calculate_path_distance(graph, path)
            pop_fitness.append((path, dist))

        pop_fitness.sort(key=lambda x: x[1])

        if pop_fitness[0][1] < best_dist:
            best_path = pop_fitness[0][0]
            best_dist = pop_fitness[0][1]

        next_gen = [pop_fitness[0][0], pop_fitness[1][0]]

        while len(next_gen) < pop_size:
            parent1 = min(random.sample(pop_fitness, min(3, len(pop_fitness))), key=lambda x: x[1])[0]
            parent2 = min(random.sample(pop_fitness, min(3, len(pop_fitness))), key=lambda x: x[1])[0]

            child = crossover(parent1, parent2, graph) if random.random() < 0.7 else parent1
            child = mutate_hybrid(graph, child, end_node, explored_order) if random.random() < 0.3 else child
            if not _is_valid_path(graph, child):
                child = parent1
            next_gen.append(child)

        population = next_gen

    return _format_result(best_dist=best_dist, best_path=best_path, explored_order=explored_order, graph=graph)

# =====================================================================
# BLOK 2: PURE GA (Menggunakan Random Walk Murni)
# =====================================================================

def pure_random_walk(graph, start_node, end_node, explored_order, max_steps=1000):
    """
    Berjalan acak (buta) dari persimpangan ke persimpangan.
    Dibatasi max_steps agar server tidak freeze/terjebak loop tak terhingga.
    """
    current = start_node
    path = [current]
    explored_order.append(current)
    
    for _ in range(max_steps):
        neighbors = list(graph.neighbors(current))
        if not neighbors:
            break # Berhenti jika masuk jalan buntu
        
        # Lempar dadu murni untuk memilih persimpangan selanjutnya
        current = random.choice(neighbors)
        path.append(current)
        explored_order.append(current)
        
        if current == end_node:
            return path
            
    return None # Gagal sampai tujuan

def mutate_pure(graph, path, end_node, explored_order):
    """Mutasi dengan Random Walk dari titik potong."""
    if len(path) <= 2:
        return path
    break_idx = random.randint(1, len(path)-2)
    break_node = path[break_idx]
    
    new_segment = pure_random_walk(graph, break_node, end_node, explored_order)
    if new_segment:
        return path[:break_idx] + new_segment[1:] # Sambungkan rute
    return path # Jika mutasi gagal/nyasar, kembalikan anak awal

def pure_ga(graph, start_node, end_node, pop_size=10, generations=20):
    explored_order = []
    population = []

    logger.info("Memulai pencarian awal Pure GA dengan Random Walk...")
    # GA Murni butuh usaha ekstra besar hanya untuk menemukan populasi awal
    attempts = 0
    max_attempts = pop_size * 50 # Maksimal 500 kali percobaan berjalan acak

    while len(population) < pop_size and attempts < max_attempts:
        path = pure_random_walk(graph, start_node, end_node, explored_order)
        if path:
            population.append(path)
        attempts += 1

    if not population:
        # Jika gagal mendapatkan 1 pun rute yang sampai tujuan
        logger.warning("Pure GA GAGAL menemukan rute ke tujuan.")
        return _format_result(best_dist=-1.0, best_path=[], explored_order=explored_order, graph=graph)

    best_path = None
    best_dist = float('inf')

    for gen in range(generations):
        pop_fitness = []
        for path in population:
            # Jika rute tidak sampai tujuan (karena gagal mutasi dll), beri penalti berat
            if path[-1] != end_node:
                pop_fitness.append((path, float('inf')))
            else:
                dist = calculate_path_distance(graph, path)
                pop_fitness.append((path, dist))

        pop_fitness.sort(key=lambda x: x[1])

        if pop_fitness[0][1] < best_dist:
            best_path = pop_fitness[0][0]
            best_dist = pop_fitness[0][1]

        # Elitisme
        next_gen = [pop_fitness[0][0], pop_fitness[1][0] if len(pop_fitness) > 1 else pop_fitness[0][0]]

        while len(next_gen) < pop_size:
            parent1 = min(random.sample(pop_fitness, min(3, len(pop_fitness))), key=lambda x: x[1])[0]
            parent2 = min(random.sample(pop_fitness, min(3, len(pop_fitness))), key=lambda x: x[1])[0]

            child = crossover(parent1, parent2, graph) if random.random() < 0.7 else parent1
            child = mutate_pure(graph, child, end_node, explored_order) if random.random() < 0.3 else child
            if not _is_valid_path(graph, child):
                child = parent1
            next_gen.append(child)

        population = next_gen

    if best_path is None or best_dist == float('inf'):
        return _format_result(best_dist=-1.0, best_path=[], explored_order=explored_order, graph=graph)

    return _format_result(best_dist=best_dist, best_path=best_path, explored_order=explored_order, graph=graph)


def _format_result(best_dist, best_path, explored_order, graph):
    """Bangun dict hasil dengan nama field yang konsisten dengan frontend (dan astar)."""
    path_coords = [(graph.nodes[n]["y"], graph.nodes[n]["x"]) for n in best_path] if best_path else []
    # `explored_coords` berisi dict {lat, lon, f, g, h} (sama seperti astar)
    # atau list koordinat polos jika path kosong. Frontend membaca `lat`/`lon` lalu
    # memakai f/g/h hanya untuk tooltip — kasih default "GA" agar tidak NaN.
    explored_coords = []
    for n in explored_order:
        explored_coords.append({
            "lat": graph.nodes[n]["y"],
            "lon": graph.nodes[n]["x"],
            "f": "GA",
            "g": "GA",
            "h": "GA",
        })
    return {
        "path_coords": path_coords,
        "distance_m": best_dist,
        "nodes_explored": len(explored_order),
        "explored_coords": explored_coords,
    }