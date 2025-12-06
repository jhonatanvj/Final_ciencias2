
"""
Versión simple e interactiva que reutiliza el B+ Tree y usa coordenadas (si existen)
para construir un grafo realista (k-NN). Menú ligero:
 1) Listar estaciones
 2) Añadir pasajeros manualmente a una estación
 3) Asignar pasajeros aleatorios (total N)
 4) Asignar pasajeros hora pico (total N)
 5) Buscar ruta mínima entre dos estaciones (y verificar/apply pax)
 6) Mostrar estado de cargas (top 10)
 7) Guardar cargas actuales a CSV
 0) Salir
"""
import os, pickle, heapq, random, csv, sys
# arriba del archivo principal
from coloreado import *
from mst_module  import *
from collections import defaultdict, deque

BPTREE_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "bplustree_transmilenio.pkl")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
if not os.path.exists(OUT_DIR): os.makedirs(OUT_DIR, exist_ok=True)

# -------------------- B+ tree helpers --------------------
def load_bplustree(path=BPTREE_PATH):
    if not os.path.exists(path):
        print("ERROR: No encontré el pickle del B+ Tree en:", path)
        sys.exit(1)
    with open(path, 'rb') as f:
        tree = pickle.load(f)
    return tree

def extract_stations_from_bpt(tree):
    # bajar a la hoja más a la izquierda
    node = tree.root
    while not getattr(node, 'leaf', False):
        node = node.children[0]
    stations = []
    while node:
        for k, vlist in zip(node.keys, node.children):
            payload = vlist[0] if vlist else {}
            name = payload.get('nom_est','') if isinstance(payload, dict) else ''
            cap = payload.get('cap_art',0) if isinstance(payload, dict) else 0
            try:
                cap = int(cap) if cap is not None else 0
            except:
                cap = 0
            lat = payload.get('lat') if isinstance(payload, dict) else None
            lon = payload.get('lon') if isinstance(payload, dict) else None
            stations.append({'code': str(k), 'name': name, 'cap': cap, 'lat': lat, 'lon': lon})
        node = getattr(node, 'next', None)
    stations.sort(key=lambda s: s['code'])
    return stations

# -------------------- Grafo realista (k-NN) --------------------
def build_realistic_graph(stations, k_neighbors=4):
    nodes = [s['code'] for s in stations]
    # map code -> coords si existen
    coords = {s['code']:(float(s['lat']), float(s['lon'])) for s in stations if s.get('lat') is not None and s.get('lon') is not None and s['lat']!='' and s['lon']!=''}
    def euclid(a,b):
        ax,ay = a; bx,by = b
        return ((ax-bx)**2 + (ay-by)**2)**0.5
    def code_weight(a,b):
        try:
            return abs(int(a) - int(b))
        except:
            return abs(sum(ord(c) for c in a) - sum(ord(c) for c in b))

    adj = {code: {} for code in nodes}

    if len(coords) >= 2:
        codes_with_coords = list(coords.keys())
        for a in codes_with_coords:
            dists = []
            for b in codes_with_coords:
                if a == b: continue
                d = euclid(coords[a], coords[b])
                dists.append((d,b))
            dists.sort()
            for d,b in dists[:k_neighbors]:
                # guardar bidireccional
                adj[a][b] = float(d)
                adj[b][a] = float(d)
        # nodos sin coords: conéctalos a vecinos por orden de código para evitar aislados
        no_coord_nodes = [c for c in nodes if not adj.get(c)]
        if no_coord_nodes:
            codes_sorted = sorted(nodes)
            N = max(2, k_neighbors)
            for i,a in enumerate(codes_sorted):
                for j in range(i+1, min(i+1+N, len(codes_sorted))):
                    b = codes_sorted[j]
                    w = code_weight(a,b)
                    adj[a][b] = w
                    adj[b][a] = w
        return adj

    # fallback: no coords en absoluto -> vecinos por orden de código
    codes_sorted = sorted(nodes)
    N = max(2, k_neighbors)
    for i,a in enumerate(codes_sorted):
        for j in range(i+1, min(i+1+N, len(codes_sorted))):
            b = codes_sorted[j]
            w = code_weight(a,b)
            adj[a][b] = w
            adj[b][a] = w
    return adj

# -------------------- Dijkstra (camino mínimo) --------------------
def dijkstra(adj, source, target):
    if source not in adj or target not in adj:
        return None, []
    dist = {source: 0}
    prev = {}
    heap = [(0, source)]
    while heap:
        d,u = heapq.heappop(heap)
        if d > dist.get(u, float('inf')): continue
        if u == target: break
        for v,w in adj[u].items():
            nd = d + w
            if nd < dist.get(v, float('inf')):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))
    if target not in dist:
        return None, []
    path = [target]
    while path[-1] != source:
        path.append(prev[path[-1]])
    path.reverse()
    return dist[target], path

# -------------------- Interactivo simple --------------------
def save_loads_csv(stations, node_loads, path=None):
    if path is None:
        path = os.path.join(OUT_DIR, 'node_loads_simple.csv')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['code','name','cap','load'])
        for s in stations:
            w.writerow([s['code'], s['name'], s['cap'], node_loads.get(s['code'],0)])
    print('Cargas guardadas en:', path)

def main_menu():
    tree = load_bplustree(BPTREE_PATH)
    stations = extract_stations_from_bpt(tree)
    code_to_station = {s['code']: s for s in stations}
    adj = build_realistic_graph(stations, k_neighbors=4)

    conflict_graph = build_conflict_graph(adj)
    station_colors = bfs_coloring(conflict_graph)   
    demanda_hora = {s['code']: max(10, s['cap']) for s in stations} 
    station_freq = {
        code: color_to_frequency(code, c, demanda_hora)
        for code, c in station_colors.items()
    }
    buses_per_station = assign_buses_from_frequency(stations, station_freq)

    # cargas actuales
    node_loads = {s['code']: 0 for s in stations}

 def option_mst():
    print("\n=== GENERANDO ÁRBOL DE RECUBRIMIENTO MÍNIMO (MST) ===")

    # EJEMPLO BÁSICO: tú después cambias las estaciones y pesos reales
    # ---------------------------------------------------------------
    # Para que funcione YA MISMO, dejo un set simple de nodos/aristas.
    # Tú luego reemplazas `stations` y `edges` con tu CSV real.
    stations = ["A", "B", "C", "D"]
    station_to_id = {name: i for i, name in enumerate(stations)}

    edges = [
        (4, station_to_id["A"], station_to_id["B"]),
        (1, station_to_id["B"], station_to_id["C"]),
        (3, station_to_id["C"], station_to_id["D"]),
        (2, station_to_id["A"], station_to_id["D"]),
    ]

    num_nodes = len(stations)

    mst_edges, cost = kruskal(num_nodes, edges)

    print("\n--- MST (Kruskal) ---")
    for w, u, v in mst_edges:
        print(f"{stations[u]} -- {stations[v]} (peso {w})")

    print(f"\nCosto total del MST: {cost}\n")


    MENU = '''\nMenú - opciones:
1) Listar estaciones (primeras 100)
2) Añadir pasajeros manualmente a una estación
3) Asignar pasajeros aleatorios (total N)
4) Asignar pasajeros hora pico (total N)
5) Buscar ruta mínima entre dos estaciones (y verificar capacidad para X pax)
6) Mostrar estado de cargas (top 10)
7) Guardar cargas actuales a CSV
8) mostrar coloreado estaciones
9) mostrar MSI (kruskal)
0) Salir
Elige una opción: '''

    while True:
        try:
            choice = input(MENU).strip()
        except (KeyboardInterrupt, EOFError):
            print('\nSaliendo.'); break

        if choice == '1':
            print(f"Mostrando hasta 100 estaciones (total estaciones: {len(stations)}):")
            for s in stations[:100]:
                print(f"{s['code']} : {s['name']} (cap={s['cap']})")
        elif choice == '2':
            code = input('Código estación (origen) -> ').strip()
            if code not in code_to_station:
                print('Código no encontrado. Usa la opción 1 o revisa.')
                continue
            try:
                n = int(input('Número de pasajeros a añadir (entero positivo) -> ').strip())
            except:
                print('Valor inválido.'); continue
            node_loads[code] += n
            print(f'Añadidos {n} pax a {code}. Carga actual: {node_loads[code]} / cap={code_to_station[code]["cap"]}')
        elif choice == '3':
            try:
                total = int(input('Total de pasajeros a distribuir aleatoriamente -> ').strip())
            except:
                print('Valor inválido.'); continue
            codes = list(node_loads.keys())
            rng = random.Random()
            for _ in range(total):
                c = rng.choice(codes)
                node_loads[c] += 1
            print(f'Distribuidos {total} pasajeros aleatoriamente entre {len(codes)} estaciones.')
        elif choice == '4':
            try:
                total = int(input('Total de pasajeros hora pico a distribuir -> ').strip())
            except:
                print('Valor inválido.'); continue
            # elegir top 10% por capacidad
            sorted_by_cap = sorted(stations, key=lambda s: s['cap'], reverse=True)
            topk = max(1, int(0.1 * len(sorted_by_cap)))
            hotspots = [s['code'] for s in sorted_by_cap[:topk]]
            rng = random.Random()
            for _ in range(total):
                c = rng.choice(hotspots)
                node_loads[c] += 1
            print(f'Distribuidos {total} pax concentrados en {len(hotspots)} estaciones (hora pico).')
        elif choice == '5':
            origin = input('Código origen -> ').strip()
            dest = input('Código destino -> ').strip()
            if origin not in code_to_station or dest not in code_to_station:
                print('Origen o destino no válidos.'); continue
            try:
                pax = int(input('¿Cuántos pasajeros quieres mover en este chequeo? (pax) -> ').strip())
            except:
                pax = 1
            dist, path = dijkstra(adj, origin, dest)
            if not path:
                print('No hay camino entre origen y destino en el grafo construido.')
                continue
            print(f'Ruta mínima ({len(path)} nodos) peso total={dist}:')
            for node in path:
                st = code_to_station[node]
                load = node_loads.get(node, 0)
                spare = max(0, st['cap'] - load)
                ok = 'OK' if spare >= pax else 'NO_CAP'
                print(f" {node} : {st['name']} (cap={st['cap']}, load={load}, spare={spare}) -> {ok}")
            spare_min = min([max(0, code_to_station[n]['cap'] - node_loads.get(n,0)) for n in path])
            if spare_min >= pax:
                print(f"La ruta soporta {pax} pax adicionales (spare_min={spare_min}).")
            elif spare_min > 0:
                print(f"La ruta solo soporta parcialmente {spare_min} pax (no full).")
            else:
                print('La ruta no soporta más pasajeros (spare_min=0).')
            apply_it = input('¿Deseas aplicar (asignar) estos pax a la ruta ahora? (s/n) -> ').strip().lower()
            if apply_it == 's':
                assign = min(pax, spare_min)
                for n in path:
                    node_loads[n] += assign
                print(f'Asignados {assign} pax a la ruta (si partial, quedó unmet={pax-assign}).')
        elif choice == '6':
            total_load = sum(node_loads.values())
            total_cap = sum([s['cap'] for s in stations])
            overloaded = [(c, node_loads[c], code_to_station[c]['cap']) for c in node_loads if code_to_station[c]['cap']>0 and node_loads[c] > code_to_station[c]['cap']]
            print(f'Total carga asignada: {total_load} | Capacidad total sumada: {total_cap} | Estaciones sobrecargadas: {len(overloaded)}')
            top = sorted(node_loads.items(), key=lambda kv: kv[1], reverse=True)[:10]
            print('Top 10 estaciones por carga:')
            for code,load in top:
                print(f" {code} : {code_to_station[code]['name']} | load={load} | cap={code_to_station[code]['cap']}")
        elif choice == '7':
            save_loads_csv(stations, node_loads)

        elif choice == '8':
            print("Asignación de buses (debug):")
            for code in sorted(buses_per_station.keys())[:100]:
                s = code_to_station[code]
                headway = station_freq[code]["headway_min"]
                demanda = demanda_hora[code]   
                color = station_colors[code]
                n_buses = buses_per_station[code]
                print(f"{code} : {s['name']} | color={color} | demanda={demanda} | headway={headway:.2f} min | buses={n_buses}")
        elif choice == '9':
            option_mst();
        elif choice == '0':
            print('Adios.'); 
            break



if __name__ == '__main__':
    main_menu()
