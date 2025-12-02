# src/loader.py
import pandas as pd
import pickle
import os
from bplustree import BPlusTree

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "Estaciones_Troncales_de_TRANSMILENIO.csv")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "bplustree_transmilenio.pkl")

def find_column_like(df_cols, target):
    norm = {c.lower().replace(" ", "").replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u"): c for c in df_cols}
    key = target.lower().replace("_","").replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
    return norm.get(key)

def build_tree(order=32):
    df = pd.read_csv(CSV_PATH, dtype=str, encoding='utf-8', low_memory=False)
    df.columns = [c.strip() for c in df.columns]

    # columnas requeridas
    required = ['nom_est', 'cod_nodo', 'cap_art']
    col_map = {}
    for c in required:
        if c in df.columns:
            col_map[c] = c
        else:
            found = find_column_like(df.columns, c)
            if found:
                col_map[c] = found
            else:
                raise ValueError(f"No se encontró columna parecida a {c} en CSV. Columnas: {df.columns.tolist()}")

    # detectar posibles columnas de coordenadas (lat/lon) en el CSV
    possible_lat_names = ['lat','latitud','latitude','y','coordy','ycoord','y_coord']
    possible_lon_names = ['lon','lng','long','longitud','x','coordx','xcoord','x_coord']
    lat_col = None
    lon_col = None
    for col in df.columns:
        low = col.lower().replace(" ", "").replace("_","")
        if low in [p.replace("_","") for p in possible_lat_names] and lat_col is None:
            lat_col = col
        if low in [p.replace("_","") for p in possible_lon_names] and lon_col is None:
            lon_col = col

    # construir lista de columnas a extraer
    cols_to_take = [col_map[c] for c in required]
    if lat_col and lon_col:
        cols_to_take += [lat_col, lon_col]

    reduced = df[cols_to_take].copy()

    # renombrar internamente a nombres estandar para facilitar
    reduced_columns = required.copy()
    if lat_col and lon_col:
        reduced_columns += ['lat','lon']
    reduced.columns = reduced_columns

    # limpiar y convertir
    reduced['cod_nodo'] = reduced['cod_nodo'].astype(str).str.strip()
    reduced['cod_nodo'] = reduced['cod_nodo'].str.replace(r'[^0-9A-Za-z_-]', '', regex=True)
    reduced['cap_art'] = pd.to_numeric(reduced['cap_art'], errors='coerce').astype('Int64')
    if 'lat' in reduced.columns and 'lon' in reduced.columns:
        reduced['lat'] = pd.to_numeric(reduced['lat'], errors='coerce')
        reduced['lon'] = pd.to_numeric(reduced['lon'], errors='coerce')

    # construir B+ Tree y persistir payloads con lat/lon si existen
    tree = BPlusTree(order=order)
    inserted = 0
    for _, row in reduced.iterrows():
        key = row['cod_nodo']
        if not key or str(key).strip() == "":
            continue
        payload = {
            'nom_est': row['nom_est'],
            'cap_art': None if pd.isna(row['cap_art']) else int(row['cap_art'])
        }
        if 'lat' in reduced.columns and not pd.isna(row['lat']) and 'lon' in reduced.columns and not pd.isna(row['lon']):
            try:
                payload['lat'] = float(row['lat'])
                payload['lon'] = float(row['lon'])
            except:
                pass
        tree.insert(key, payload)
        inserted += 1

    # guardar pickle
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'wb') as f:
        pickle.dump(tree, f)

    print(f"Insertados: {inserted}. Árbol guardado en: {OUT_PATH}")
    return OUT_PATH

if __name__ == "__main__":
    build_tree()
