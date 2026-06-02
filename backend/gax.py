import random
import logging
import networkx as nx

logger = logging.getLogger(__name__)

def calculate_path_distance(graph, path):
    """Menghitung total jarak rute nyata dari rentetan node (kromosom)."""
    dist = 0.0
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i+1]
        # Mengambil data jalan (edge) terpendek yang menyambungkan 2 node
        edge_data = graph.get_edge_data(u, v)
        min_len = min(d.get("length", float("inf")) for d in edge_data.values())
        dist += min_len
    return dist

def generate_random_path(graph, start_node, end_node, explored_order):
    """
    Membangkitkan rute yang PASTI SAMPAI ke tujuan untuk Kromosom awal.
    Trik: Kita mengacak bobot/jarak asli jalanan secara sementara, lalu mencari
    rute terpendek. Ini menghasilkan rute yang valid, tapi sengaja dibuat 
    lewat jalan memutar yang bervariasi untuk bahan evolusi GA.
    """
    # 1. Tambahkan bobot "gangguan/noise" pada graf
    for u, v, k, data in graph.edges(keys=True, data=True):
        length = data.get("length", 10.0)
        # Kalikan jarak jalan asli dengan angka acak antara 1x hingga 5x lipat
        data["temp_weight"] = length * random.uniform(1.0, 5.0)
        
    try:
        # 2. Cari rute menggunakan graf yang jaraknya sudah "dikacaukan"
        path = nx.shortest_path(graph, source=start_node, target=end_node, weight="temp_weight")
        
        # 3. Catat beberapa node untuk dianimasikan sebagai titik "Eksplorasi Mutasi" di Peta UI
        step = max(1, len(path) // 5)
        for n in path[::step]:
            explored_order.append({
                "lat": graph.nodes[n]["y"],
                "lon": graph.nodes[n]["x"],
                "f": "GA", "g": "Node", "h": "Evolusi"
            })
            
        return path
    except nx.NetworkXNoPath:
        return None

def crossover(path1, path2):
    """
    Kombinasi 2 rute (Crossover). 
    Mencari persimpangan jalan yang kebetulan sama-sama dilewati oleh Parent 1 dan Parent 2,
    lalu menempelkan potongan rute Parent 1 ke rute Parent 2.
    """
    # Cari simpang yang sama antara kedua rute (kecuali titik awal dan akhir)
    common_nodes = list(set(path1[1:-1]).intersection(set(path2[1:-1])))
    
    if not common_nodes:
        return path1 # Jika rutenya benar-benar beda dan tidak pernah berpotongan, gagalkan crossover

    # Pilih 1 persimpangan secara acak sebagai titik potong
    crossover_point = random.choice(common_nodes)
    idx1 = path1.index(crossover_point)
    idx2 = path2.index(crossover_point)

    # Sambungkan: Start -> Parent 1 -> (Titik Potong) -> Parent 2 -> Tujuan
    new_path = path1[:idx1] + path2[idx2:]
    return new_path

def mutate(graph, path, end_node, explored_order):
    """
    Mutasi Rute.
    Mengambil sebuah rute, dipotong di tengah-tengah jalan secara acak, 
    lalu memaksa mencari jalan memutar baru dari titik potongan tersebut ke tujuan.
    """
    if len(path) <= 2:
        return path
    
    # Pilih persimpangan acak di tengah-tengah rute saat ini
    break_idx = random.randint(1, len(path) - 2)
    break_node = path[break_idx]

    # Bangkitkan jalan variasi baru dari persimpangan tersebut menuju tujuan
    new_segment = generate_random_path(graph, break_node, end_node, explored_order)
    
    if new_segment:
        # Tempelkan jalan lama dengan jalan mutasi baru
        return path[:break_idx] + new_segment
    return path

def genetic_algorithm(graph, start_node, end_node, pop_size=10, generations=20):
    """Fungsi Utama Algoritma Genetika"""
    explored_order = []
    population = []

    # ==========================================
    # 1. INISIALISASI POPULASI
    # ==========================================
    for _ in range(pop_size):
        p = generate_random_path(graph, start_node, end_node, explored_order)
        if p:
            population.append(p)

    if not population:
        raise ValueError("GA gagal menemukan rute awal yang valid.")

    best_path = None
    best_dist = float('inf')

    # ==========================================
    # 2. SIKLUS EVOLUSI (Berdasarkan Generasi)
    # ==========================================
    for gen in range(generations):
        # Hitung Fitness: Jarak (Semakin pendek jarak, semakin baik rank-nya)
        pop_fitness = [(p, calculate_path_distance(graph, p)) for p in population]
        pop_fitness.sort(key=lambda x: x[1])

        # Simpan rekor rute terbaik
        if pop_fitness[0][1] < best_dist:
            best_path = pop_fitness[0][0]
            best_dist = pop_fitness[0][1]

        # ELITISME: Otomatis loloskan 2 rute terbaik ke generasi berikutnya
        next_gen = [pop_fitness[0][0], pop_fitness[1][0]] 

        # PROSES KAWIN SILANG (CROSSOVER) & MUTASI
        while len(next_gen) < pop_size:
            # Seleksi Turnamen: Ambil acak 3, lalu pilih yang jaraknya terpendek jadi orang tua
            parent1 = min(random.sample(pop_fitness, min(3, len(pop_fitness))), key=lambda x: x[1])[0]
            parent2 = min(random.sample(pop_fitness, min(3, len(pop_fitness))), key=lambda x: x[1])[0]

            # 70% Peluang Crossover
            if random.random() < 0.7:
                child = crossover(parent1, parent2)
            else:
                child = parent1

            # 30% Peluang Mutasi 
            if random.random() < 0.3:
                child = mutate(graph, child, end_node, explored_order)

            next_gen.append(child)

        # Ganti populasi lama dengan generasi baru
        population = next_gen

    # Konversi ID node jalanan kembali menjadi latitude/longitude agar bisa digambar di peta
    coords = [(graph.nodes[n]["y"], graph.nodes[n]["x"]) for n in best_path]

    return {
        "path_nodes": best_path,
        "path_coords": coords,
        "distance_m": best_dist,
        "nodes_explored": len(explored_order),
        "explored_coords": explored_order,
    }