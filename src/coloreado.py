from collections import deque
import math

# Construye un grafo de conflictos no dirigido a partir de la lista de adyacencias
def build_conflict_graph(adj):
    conflict = {u: set() for u in adj}
    for u in adj:
        for v in adj[u]:
            conflict[u].add(v)   
            conflict[v].add(u)   # asegura simetría en el grafo no dirigido
    return conflict


# Colorea el grafo usando BFS: asigna el menor color disponible para cada nodo
def bfs_coloring(conflict_graph):
    colors = {}
    visited = set()

    for start in conflict_graph:  # por si el grafo tiene varios componentes
        if start in visited:
            continue

        queue = deque([start])
        visited.add(start)

        while queue:
            node = queue.popleft()

            # Colores ya usados por vecinos del nodo
            used = {colors[n] for n in conflict_graph[node] if n in colors}

            # Asigna el primer color disponible
            c = 0
            while c in used:
                c += 1
            colors[node] = c

            # Encola vecinos aún no visitados
            for neigh in conflict_graph[node]:
                if neigh not in visited:
                    visited.add(neigh)
                    queue.append(neigh)

    return colors


# Devuelve un factor según el color asignado (representa la prioridad de la estacion)
def color_priority_factor(color_id):
    if color_id == 0: return 0.7 
    if color_id == 1: return 0.9
    if color_id == 2: return 1.0
    if color_id == 3: return 1.2
    return 1.4       


# Calcula la frecuencia de buses según el color y demanda estimada
def color_to_frequency(code, color_id, demanda_hora, cap_bus=160):
    d = max(1, demanda_hora.get(code, 1))  # demanda mínima en una hora
    cap_eff = cap_bus * 0.3                # capacidad efectiva usada (30%)
    freq_teorica = d / cap_eff             # buses/h necesarios
    headway_base = 60 / freq_teorica       # intervalo base en minutos
    factor = color_priority_factor(color_id)
    headway = headway_base * factor        # ajusta por prioridad del color

    # Limita la frecuencia enntre un rango de 2 y 25
    headway = max(2, min(headway, 25))
    return {"headway_min": headway}


# Construye una lista de pesos para selección aleatoria ponderada
def build_service_weights(stations, station_freq):
    weights = []
    for s in stations:
        code = s['code']
        freq = station_freq[code]["headway_min"]
        w = 1.0 / freq  # mayor frecuencia = mayor peso
        weights.append((code, w))
    return weights


# Escoge un elemento según sus pesos al azar
def weighted_choice(weights, rng):
    total = sum(w for _, w in weights)
    r = rng.random() * total
    acc = 0
    for code, w in weights:
        acc += w
        if acc >= r:
            return code


HORIZON_MIN = 60  # asignacion de buses en un intervalo de 60 minutos


# Calcula cuántos buses requiere cada estación según su frecuencia
def assign_buses_from_frequency(stations, station_freq, horizon_min=HORIZON_MIN):
    buses_per_station = {}
    for s in stations:
        code = s['code']
        headway = station_freq[code]["headway_min"]

        # Número de buses necesarios en ese horizonte de tiempo
        if headway <= 0:
            n_buses = 0
        else:
            n_buses = math.ceil(horizon_min / headway)

        buses_per_station[code] = n_buses

    return buses_per_station
