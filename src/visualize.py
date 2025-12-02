# src/visualize.py
import pandas as pd
import os
import folium
import matplotlib.pyplot as plt

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "Estaciones_Troncales_de_TRANSMILENIO.csv")

def load_reduced():
    df = pd.read_csv(CSV_PATH, dtype=str, encoding='utf-8', low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    # columnas principales
    # intento mapear lat/lon si existen
    nom_col = None
    cod_col = None
    cap_col = None
    lat_col = None
    lon_col = None
    for c in df.columns:
        cl = c.lower().replace(" ", "")
        if cl in ["nom_est","nombres","estacion","nombre"]:
            nom_col = c
        if cl in ["cod_nodo","codnodo","codigo","id"]:
            cod_col = c
        if cl in ["cap_art","capacidad","capacidad_art","capacidad_max"]:
            cap_col = c
        if cl in ["lat","latitude","latitud"]:
            lat_col = c
        if cl in ["lon","longitude","longitud","lng"]:
            lon_col = c

    # fallback a los nombres exactos pedidos
    if not nom_col and 'nom_est' in df.columns:
        nom_col = 'nom_est'
    if not cod_col and 'cod_nodo' in df.columns:
        cod_col = 'cod_nodo'
    if not cap_col and 'cap_art' in df.columns:
        cap_col = 'cap_art'

    reduced = df[[c for c in [nom_col, cod_col, cap_col] if c is not None]].copy()
    reduced.columns = ['nom_est', 'cod_nodo', 'cap_art']
    reduced['cap_art'] = pd.to_numeric(reduced['cap_art'], errors='coerce').fillna(0).astype(int)
    return reduced, lat_col, lon_col, df

def folium_map(output_html="outputs/estaciones_map.html"):
    reduced, lat_col, lon_col, raw_df = load_reduced()
    if lat_col is None or lon_col is None:
        print("No se encontraron columnas de lat/lon en el CSV. Usa 'barplot_top' en su lugar.")
        return None

    # construir mapa centrado en promedio de coordenadas
    raw_df[lat_col] = pd.to_numeric(raw_df[lat_col], errors='coerce')
    raw_df[lon_col] = pd.to_numeric(raw_df[lon_col], errors='coerce')
    raw_df = raw_df.dropna(subset=[lat_col, lon_col])
    center = [raw_df[lat_col].mean(), raw_df[lon_col].mean()]
    m = folium.Map(location=center, zoom_start=12)
    for _, r in raw_df.iterrows():
        popup = f"{r.get('nom_est','')} (cod:{r.get('cod_nodo','')})<br>cap:{r.get('cap_art','')}"
        folium.Marker([r[lat_col], r[lon_col]], popup=popup).add_to(m)
    os.makedirs(os.path.dirname(output_html), exist_ok=True)
    m.save(output_html)
    print(f"Mapa guardado en {output_html}")
    return output_html

def barplot_top(n=20, output_img="outputs/top_capacidad.png"):
    reduced, *_ = load_reduced()
    top = reduced.sort_values(by='cap_art', ascending=False).head(n)
    plt.figure(figsize=(10,6))
    plt.barh(top['nom_est'][::-1], top['cap_art'][::-1])
    plt.xlabel("Capacidad (cap_art)")
    plt.title(f"Top {n} estaciones por capacidad")
    os.makedirs(os.path.dirname(output_img), exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_img)
    print(f"Barplot guardado en {output_img}")
    return output_img

if __name__ == "__main__":
    # intenta crear mapa; si no hay coords crea barplot
    res = folium_map()
    if res is None:
        barplot_top(25)
