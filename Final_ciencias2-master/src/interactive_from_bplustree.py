import os, pickle, heapq, random, csv, sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from coloreado import build_conflict_graph, bfs_coloring, color_to_frequency, assign_buses_from_frequency
from mst_module import kruskal


#  RUTAS Y B+ TREE

BASE_DIR = os.path.dirname(__file__)
BPTREE_PATH = os.path.join(BASE_DIR, "..", "outputs", "bplustree_transmilenio.pkl")
OUT_DIR = os.path.join(BASE_DIR, "..", "outputs")
os.makedirs(OUT_DIR, exist_ok=True)


def load_bplustree(path=BPTREE_PATH):
    if not os.path.exists(path):
        messagebox.showerror("Error", f"No encontré el pickle del B+ Tree:\n{path}")
        sys.exit(1)
    with open(path, 'rb') as f:
        tree = pickle.load(f)
    return tree


def extract_stations_from_bpt(tree):
    node = tree.root
    while not getattr(node, 'leaf', False):
        node = node.children[0]

    stations = []
    while node:
        for k, vlist in zip(node.keys, node.children):
            payload = vlist[0] if vlist else {}
            if not isinstance(payload, dict):
                payload = {}
            name = payload.get('nom_est', '') or ''
            cap = payload.get('cap_art', 0) or 0
            try:
                cap = int(cap)
            except Exception:
                cap = 0
            lat = payload.get('lat')
            lon = payload.get('lon')
            stations.append({
                'code': str(k),
                'name': name,
                'cap': cap,
                'lat': lat,
                'lon': lon
            })
        node = getattr(node, 'next', None)

    stations.sort(key=lambda s: s['code'])
    return stations



#  GRAFO, DIJKSTRA, CSV, MST

def build_realistic_graph(stations, k_neighbors=4):
    nodes = [s['code'] for s in stations]
    coords = {
        s['code']: (float(s['lat']), float(s['lon']))
        for s in stations
        if s.get('lat') not in (None, '') and s.get('lon') not in (None, '')
    }

    def euclid(a, b):
        ax, ay = a
        bx, by = b
        return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5

    def code_weight(a, b):
        try:
            return abs(int(a) - int(b))
        except Exception:
            return abs(sum(ord(c) for c in a) - sum(ord(c) for c in b))

    adj = {code: {} for code in nodes}

    if len(coords) >= 2:
        codes_with_coords = list(coords.keys())
        for a in codes_with_coords:
            dists = []
            for b in codes_with_coords:
                if a == b:
                    continue
                d = euclid(coords[a], coords[b])
                dists.append((d, b))
            dists.sort()
            for d, b in dists[:k_neighbors]:
                adj[a][b] = float(d)
                adj[b][a] = float(d)

        no_coord_nodes = [c for c in nodes if not adj.get(c)]
        if no_coord_nodes:
            codes_sorted = sorted(nodes)
            N = max(2, k_neighbors)
            for i, a in enumerate(codes_sorted):
                for j in range(i + 1, min(i + 1 + N, len(codes_sorted))):
                    b = codes_sorted[j]
                    w = code_weight(a, b)
                    adj[a][b] = w
                    adj[b][a] = w
        return adj

    codes_sorted = sorted(nodes)
    N = max(2, k_neighbors)
    for i, a in enumerate(codes_sorted):
        for j in range(i + 1, min(i + 1 + N, len(codes_sorted))):
            b = codes_sorted[j]
            w = code_weight(a, b)
            adj[a][b] = w
            adj[b][a] = w
    return adj


def dijkstra(adj, source, target):
    if source not in adj or target not in adj:
        return None, []

    dist = {source: 0.0}
    prev = {}
    heap = [(0.0, source)]

    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, float('inf')):
            continue
        if u == target:
            break
        for v, w in adj[u].items():
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


def save_loads_csv(stations, node_loads, path=None):
    if path is None:
        path = os.path.join(OUT_DIR, 'node_loads_simple.csv')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['code', 'name', 'cap', 'load'])
        for s in stations:
            w.writerow([
                s['code'],
                s['name'],
                s['cap'],
                node_loads.get(s['code'], 0)
            ])
    messagebox.showinfo("CSV", f"Cargas guardadas en:\n{path}")


def demo_mst():
    mst_nodes = ["A", "B", "C", "D"]
    node_to_id = {name: i for i, name in enumerate(mst_nodes)}
    edges = [
        (4, node_to_id["A"], node_to_id["B"]),
        (1, node_to_id["B"], node_to_id["C"]),
        (3, node_to_id["C"], node_to_id["D"]),
        (2, node_to_id["A"], node_to_id["D"]),
    ]
    mst_edges, cost = kruskal(len(mst_nodes), edges)
    lines = ["MST (Kruskal):"]
    for w, u, v in mst_edges:
        lines.append(f"{mst_nodes[u]} -- {mst_nodes[v]}  (peso {w})")
    lines.append(f"\nCosto total: {cost}")
    messagebox.showinfo("MST demo", "\n".join(lines))



#  GUI TKINTER

class TransitGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulador TransMilenio - GUI")
        self.geometry("950x600")

        # datos base
        tree = load_bplustree()
        self.stations = extract_stations_from_bpt(tree)
        self.code_to_station = {s['code']: s for s in self.stations}
        self.adj = build_realistic_graph(self.stations, k_neighbors=4)

        conflict_graph = build_conflict_graph(self.adj)
        self.station_colors = bfs_coloring(conflict_graph)

        self.demanda_hora = {s['code']: max(10, s['cap']) for s in self.stations}
        self.station_freq = {
            code: color_to_frequency(code, c, self.demanda_hora)
            for code, c in self.station_colors.items()
        }
        self.buses_per_station = assign_buses_from_frequency(self.stations,
                                                             self.station_freq)

        self.node_loads = {s['code']: 0 for s in self.stations}

        self._build_widgets()

    # ---------------- widgets principales ----------------
    def _build_widgets(self):
        # marco izquierdo: lista de estaciones
        left = tk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        tk.Label(left, text="Estaciones").pack()
        self.listbox = tk.Listbox(left, width=30)
        self.listbox.pack(fill=tk.Y, expand=True)
        for s in self.stations:
            self.listbox.insert(tk.END, f"{s['code']} - {s['name']}")

        # marco central: texto de salida
        center = tk.Frame(self)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(center, text="Salida / Log").pack()
        self.text = tk.Text(center, wrap="word")
        self.text.pack(fill=tk.BOTH, expand=True)

        # marco derecho: botones (equivalentes al menú)
        right = tk.Frame(self)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        tk.Label(right, text="Acciones").pack()

        tk.Button(right, text="1) Listar estaciones",
                  command=self.action_list_stations).pack(fill=tk.X, pady=2)
        tk.Button(right, text="2) Añadir pasajeros a estación",
                  command=self.action_add_pax_manual).pack(fill=tk.X, pady=2)
        tk.Button(right, text="3) Pax aleatorios",
                  command=self.action_add_pax_random).pack(fill=tk.X, pady=2)
        tk.Button(right, text="4) Pax hora pico",
                  command=self.action_add_pax_peak).pack(fill=tk.X, pady=2)
        tk.Button(right, text="5) Ruta mínima y capacidad",
                  command=self.action_shortest_path).pack(fill=tk.X, pady=2)
        tk.Button(right, text="6) Estado de cargas",
                  command=self.action_show_loads).pack(fill=tk.X, pady=2)
        tk.Button(right, text="7) Guardar cargas CSV",
                  command=self.action_save_csv).pack(fill=tk.X, pady=2)
        tk.Button(right, text="8) Coloreado / buses",
                  command=self.action_show_coloring).pack(fill=tk.X, pady=2)
        tk.Button(right, text="9) MST demo",
                  command=self.action_mst).pack(fill=tk.X, pady=2)
        tk.Button(right, text="Salir", command=self.destroy).pack(fill=tk.X, pady=10)

    # ---------------- helpers GUI ----------------
    def log(self, msg):
        self.text.insert(tk.END, msg + "\n")
        self.text.see(tk.END)

    def ask_station_code(self, prompt):
        code = simpledialog.askstring("Estación", prompt)
        if not code:
            return None
        code = code.strip()
        if code not in self.code_to_station:
            messagebox.showerror("Error", "Código de estación no válido.")
            return None
        return code

    # ---------------- acciones equivalentes al menú ----------------
    def action_list_stations(self):
        self.text.delete("1.0", tk.END)
        self.log(f"Mostrando hasta 100 estaciones (total {len(self.stations)}):")
        for s in self.stations[:100]:
            self.log(f"{s['code']} : {s['name']} (cap={s['cap']})")

    def action_add_pax_manual(self):
        code = self.ask_station_code("Código estación (origen):")
        if not code:
            return
        try:
            n = int(simpledialog.askstring("Pasajeros",
                                           "Número de pasajeros a añadir:"))
        except Exception:
            messagebox.showerror("Error", "Valor inválido.")
            return
        self.node_loads[code] += n
        st = self.code_to_station[code]
        self.log(f"Añadidos {n} pax a {code}. Carga={self.node_loads[code]} / cap={st['cap']}")

    def action_add_pax_random(self):
        try:
            total = int(simpledialog.askstring("Pax aleatorios",
                                               "Total de pasajeros a distribuir:"))
        except Exception:
            messagebox.showerror("Error", "Valor inválido.")
            return
        codes = list(self.node_loads.keys())
        rng = random.Random()
        for _ in range(total):
            c = rng.choice(codes)
            self.node_loads[c] += 1
        self.log(f"Distribuidos {total} pasajeros aleatoriamente entre {len(codes)} estaciones.")

    def action_add_pax_peak(self):
        try:
            total = int(simpledialog.askstring("Pax hora pico",
                                               "Total de pasajeros hora pico:"))
        except Exception:
            messagebox.showerror("Error", "Valor inválido.")
            return
        sorted_by_cap = sorted(self.stations, key=lambda s: s['cap'], reverse=True)
        topk = max(1, int(0.1 * len(sorted_by_cap)))
        hotspots = [s['code'] for s in sorted_by_cap[:topk]]
        rng = random.Random()
        for _ in range(total):
            c = rng.choice(hotspots)
            self.node_loads[c] += 1
        self.log(f"Distribuidos {total} pax en {len(hotspots)} estaciones (hora pico).")

    def action_shortest_path(self):
        origin = self.ask_station_code("Código origen:")
        if not origin:
            return
        dest = self.ask_station_code("Código destino:")
        if not dest:
            return
        try:
            pax = int(simpledialog.askstring("Pasajeros",
                                             "¿Cuántos pasajeros quieres mover?"))
        except Exception:
            pax = 1
        dist, path = dijkstra(self.adj, origin, dest)
        if not path:
            messagebox.showinfo("Ruta", "No hay camino entre origen y destino.")
            return
        self.text.delete("1.0", tk.END)
        self.log(f"Ruta mínima ({len(path)} nodos) peso total={dist}:")
        spare_list = []
        for node in path:
            st = self.code_to_station[node]
            load = self.node_loads.get(node, 0)
            spare = max(0, st['cap'] - load)
            spare_list.append(spare)
            ok = 'OK' if spare >= pax else 'NO_CAP'
            self.log(f"{node} : {st['name']} (cap={st['cap']}, load={load}, spare={spare}) -> {ok}")
        spare_min = min(spare_list)
        if spare_min >= pax:
            self.log(f"La ruta soporta {pax} pax adicionales (spare_min={spare_min}).")
        elif spare_min > 0:
            self.log(f"La ruta solo soporta parcialmente {spare_min} pax.")
        else:
            self.log("La ruta no soporta más pasajeros.")
        if messagebox.askyesno("Aplicar", "¿Aplicar estos pax a la ruta?"):
            assign = min(pax, spare_min)
            for n in path:
                self.node_loads[n] += assign
            self.log(f"Asignados {assign} pax a la ruta.")

    def action_show_loads(self):
        total_load = sum(self.node_loads.values())
        total_cap = sum(s['cap'] for s in self.stations)
        overloaded = [
            (c, self.node_loads[c], self.code_to_station[c]['cap'])
            for c in self.node_loads
            if self.code_to_station[c]['cap'] > 0
            and self.node_loads[c] > self.code_to_station[c]['cap']
        ]
        self.text.delete("1.0", tk.END)
        self.log(f"Total carga: {total_load} | Capacidad total: {total_cap} | "
                 f"Estaciones sobrecargadas: {len(overloaded)}")
        top = sorted(self.node_loads.items(), key=lambda kv: kv[1], reverse=True)[:10]
        self.log("Top 10 estaciones por carga:")
        for code, load in top:
            s = self.code_to_station[code]
            self.log(f"{code} : {s['name']} | load={load} | cap={s['cap']}")

    def action_save_csv(self):
        save_loads_csv(self.stations, self.node_loads)

    def action_show_coloring(self):
        self.text.delete("1.0", tk.END)
        self.log("Coloreado y asignación de buses:")
        for code in sorted(self.buses_per_station.keys())[:100]:
            s = self.code_to_station[code]
            headway = self.station_freq[code]["headway_min"]
            demanda = self.demanda_hora[code]
            color = self.station_colors[code]
            n_buses = self.buses_per_station[code]
            self.log(f"{code} : {s['name']} | color={color} | demanda={demanda} | "
                     f"headway={headway:.2f} min | buses={n_buses}")

    def action_mst(self):
        demo_mst()


if __name__ == "__main__":
    app = TransitGUI()
    app.mainloop()
