import random
import logging
import networkx as nx
from astar import _haversine

logger = logging.getLogger(__name__)

def calculate_path_distance(graph, path):
    """Menghitung total jarak rute yang dihasilkan."""
    dist = 0.0
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i+1]
        # Mengambil edge terpendek jika ada multi-graph
        edge_data = graph.get_edge_data(u, v)
        min_len = min(d.get("length", float("inf")) for d in edge_data.values())
        dist += min_len
    return dist

def generate_random_path(graph, start_node, end_node, explored_order):
    """Membangkitkan rute acak yang berbias (terarah ke tujuan) untuk populasi awal dan mutasi."""
    end_lat = graph.nodes[end_node]["y"]
    end_lon = graph.nodes[end_node]["x"]

    path = [start_node]
    current = start_node
    visited = {start_node}

    while current != end_node:
        neighbors = list(graph.neighbors(current))
        valid_neighbors = [n for n in neighbors if n not in visited]

        if not valid_neighbors:
            return None # Menemukan jalan buntu (dead end)

        # Mengurutkan tetangga berdasarkan kedekatan dengan titik tujuan (heuristik)
        def dist_to_end(n):
            return _haversine(graph.nodes[n]["y"], graph.nodes[n]["x"], end_lat, end_lon)

        valid_neighbors.sort(key=dist_to_end)

        # Pilih secara acak dari 3 tetangga terbaik (memberikan unsur probabilitas GA)
        next_node = random.choice(valid_neighbors[:3])

        # Catat eksplorasi node untuk animasi di frontend
        explored_order.append({
            "lat": graph.nodes[next_node]["y"],
            "lon": graph.nodes[next_node]["x"],
            "f": "GA", "g": "N/A", "h": "N/A"
        })

        path.append(next_node)
        visited.add(next_node)
        current = next_node

        # Keamanan agar loop tidak berjalan tak terbatas
        if len(path) > 2000:
            return None

    return path

def crossover(path1, path2):
    """Mengkombinasikan dua rute berdasarkan titik pertemuan (irisan) yang sama."""
    common_nodes = list(set(path1[1:-1]).intersection(set(path2[1:-1])))
    if not common_nodes:
        return path1 # Jika tidak ada persimpangan yang sama, pertahankan rute awal

    # Pilih satu titik potong secara acak
    crossover_point = random.choice(common_nodes)
    idx1 = path1.index(crossover_point)
    idx2 = path2.index(crossover_point)

    # Gabungkan bagian awal parent 1 dan bagian akhir parent 2
    prefix = path1[:idx1]
    suffix = path2[idx2:]
    prefix_set = set(prefix)
    # Jika suffix mengandung node yang sudah ada di prefix (siklus), fallback
    if prefix_set.intersection(set(suffix[1:])):
        return path1
    return prefix + suffix

def mutate(graph, path, end_node, explored_order):
    """Melakukan mutasi dengan memutus rute di tengah, lalu mencari rute baru ke tujuan."""
    if len(path) <= 2:
        return path
    
    break_idx = random.randint(1, len(path) - 2)
    break_node = path[break_idx]

    # Bangkitkan segmen baru dari titik patahan ke tujuan
    new_segment = generate_random_path(graph, break_node, end_node, explored_order)
    if new_segment:
        return path[:break_idx] + new_segment
    return path

def genetic_algorithm(graph, start_node, end_node, pop_size=10, generations=20):
    """Algoritma Genetika utama untuk pencarian rute."""
    explored_order = []
    population = []

    # 1. Inisialisasi Populasi
    # Gunakan shortest path sebagai jaminan satu rute valid
    try:
        shortest = nx.shortest_path(graph, start_node, end_node, weight="length")
        population.append(shortest)
    except nx.NetworkXNoPath:
        raise ValueError("GA gagal menemukan rute awal yang valid. Coba titik lain.")

    # Tambahkan rute acak berbias untuk mengisi populasi
    for _ in range(pop_size * 3):
        if len(population) >= pop_size:
            break
        p = generate_random_path(graph, start_node, end_node, explored_order)
        if p and p not in population:
            population.append(p)

    best_path = None
    best_dist = float('inf')

    # 2. Siklus Evolusi
    for gen in range(generations):
        # Hitung Fitness (Semakin pendek jarak, semakin baik)
        pop_fitness = [(p, calculate_path_distance(graph, p)) for p in population]
        pop_fitness.sort(key=lambda x: x[1])

        # Simpan rute terbaik (Elitism)
        if pop_fitness[0][1] < best_dist:
            best_path = pop_fitness[0][0]
            best_dist = pop_fitness[0][1]

        elite_count = min(2, len(pop_fitness))
        next_gen = [pop_fitness[i][0] for i in range(elite_count)] # Bawa rute terbaik ke generasi selanjutnya

        # Crossover & Mutasi
        while len(next_gen) < pop_size:
            # Seleksi Turnamen
            parent1 = min(random.sample(pop_fitness, min(3, len(pop_fitness))), key=lambda x: x[1])[0]
            parent2 = min(random.sample(pop_fitness, min(3, len(pop_fitness))), key=lambda x: x[1])[0]

            # Probabilitas Crossover 70%
            if random.random() < 0.7:
                child = crossover(parent1, parent2)
            else:
                child = parent1

            # Probabilitas Mutasi 30%
            if random.random() < 0.3:
                child = mutate(graph, child, end_node, explored_order)

            next_gen.append(child)

        population = next_gen

    coords = [(graph.nodes[n]["y"], graph.nodes[n]["x"]) for n in best_path]

    return {
        "path_nodes": best_path,
        "path_coords": coords,
        "distance_m": best_dist,
        "nodes_explored": len(explored_order),
        "explored_coords": explored_order,
    }