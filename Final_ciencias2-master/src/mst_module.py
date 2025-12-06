# mst_module.py
# Implementación sencilla de Kruskal para obtener el Árbol de Recubrimiento Mínimo (MST)

class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        rootX = self.find(x)
        rootY = self.find(y)

        if rootX != rootY:
            if self.rank[rootX] < self.rank[rootY]:
                self.parent[rootX] = rootY
            elif self.rank[rootX] > self.rank[rootY]:
                self.parent[rootY] = rootX
            else:
                self.parent[rootY] = rootX
                self.rank[rootX] += 1
            return True
        return False


def kruskal(num_nodes, edges):
    """
    num_nodes: cantidad de nodos (0..num_nodes-1)
    edges: lista de tuplas (peso, u, v)

    retorna:
      mst_edges -> lista de aristas del MST: (peso, u, v)
      mst_cost  -> suma total de pesos
    """

    # Ordenar aristas por peso
    edges_sorted = sorted(edges, key=lambda x: x[0])

    uf = UnionFind(num_nodes)

    mst_edges = []
    mst_cost = 0

    for weight, u, v in edges_sorted:
        if uf.union(u, v):
            mst_edges.append((weight, u, v))
            mst_cost += weight

        # Si ya tenemos num_nodes-1 aristas, paramos
        if len(mst_edges) == num_nodes - 1:
            break

    return mst_edges, mst_cost


# Ejemplo de uso (lo puedes borrar si quieres):
if __name__ == "__main__":
    num_nodes = 4
    edges = [
        (1, 0, 1),
        (4, 0, 2),
        (3, 1, 2),
        (2, 1, 3),
        (5, 2, 3)
    ]

    mst, cost = kruskal(num_nodes, edges)
    print("MST:", mst)
    print("Costo total:", cost)
