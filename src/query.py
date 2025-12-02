# src/query.py
import pickle
import os
from pprint import pprint

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "bplustree_transmilenio.pkl")

def load_tree(path=OUT_PATH):
    with open(path, 'rb') as f:
        tree = pickle.load(f)
    return tree

def buscar_clave(key):
    tree = load_tree()
    res = tree.search(key)
    print(f"Resultado búsqueda clave={key}:")
    pprint(res)

def buscar_rango(low, high):
    tree = load_tree()
    res = tree.range_search(low, high)
    print(f"Resultados rango {low} .. {high}: (cantidad {len(res)})")
    for k, items in res:
        print(k, "->", items)

if __name__ == "__main__":
    # ejemplos
    buscar_clave("7103")
    buscar_rango("7100", "7120")
