import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, MultiPoint, Polygon   # <-- TAMBAHKAN Polygon
from shapely import wkt
import networkx as nx
import folium
import numpy as np
from pyproj import CRS, Transformer
import time
from scipy.spatial import cKDTree

# ----------------------------
# 1. KONFIGURASI
# ----------------------------
FILE_PATH = 'traffic_data.csv'
ORIGIN_POINT = (24.3233, 54.6909)       # (lat, lon) titik pusat Anda
TIME_LIMITS = [5, 10, 20, 30]           # menit
COLORS = ['green', 'yellow', 'orange', 'red']
SPEED_COLUMN = 'average_speed_kmh'
ROUND_DECIMALS = 6                      # Presisi penggabungan simpul (meter)

# ----------------------------
# 2. BACA & BERSIHKAN DATA
# ----------------------------
print("Membaca data...")
df = pd.read_csv(FILE_PATH)
df['geometry'] = df['geometry'].apply(wkt.loads)
gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")

gdf = gdf.dropna(subset=[SPEED_COLUMN])
gdf = gdf[gdf[SPEED_COLUMN] > 0]
print(f"Total segmen valid: {len(gdf)}")

# ----------------------------
# 3. EKSTRAK SEMUA SEGMEN (START-END) DENGAN KECEPATAN
# ----------------------------
print("Mengekstrak segmen jalan...")
edges_raw = []   # (start_lon, start_lat, end_lon, end_lat, speed)

for geom, speed in zip(gdf.geometry, gdf[SPEED_COLUMN]):
    coords = list(geom.coords)
    for i in range(len(coords) - 1):
        start, end = coords[i], coords[i+1]
        edges_raw.append((start[0], start[1], end[0], end[1], speed))

print(f"Total segmen hasil ekstraksi: {len(edges_raw)}")

# ----------------------------
# 4. BUAT ID UNTUK SEMUA TITIK UNIK (DENGAN PEMBULATAN)
# ----------------------------
def round_coord(lon, lat):
    return (round(lon, ROUND_DECIMALS), round(lat, ROUND_DECIMALS))

all_points = set()
for slon, slat, elon, elat, _ in edges_raw:
    all_points.add(round_coord(slon, slat))
    all_points.add(round_coord(elon, elat))

node_list = list(all_points)
node_to_id = {pt: i for i, pt in enumerate(node_list)}
n_nodes = len(node_to_id)
print(f"Jumlah simpul unik: {n_nodes}")

# ----------------------------
# 5. TRANSFORMASI PROYEKSI MASSAL & HITUNG WAKTU TEMPUH
# ----------------------------
transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

lons_arr = np.array([pt[0] for pt in node_list])
lats_arr = np.array([pt[1] for pt in node_list])
x_arr, y_arr = transformer.transform(lons_arr, lats_arr)

id_to_xy = {i: (x_arr[i], y_arr[i]) for i in range(n_nodes)}

print("Menghitung bobot waktu edge...")
edges_for_nx = []

for slon, slat, elon, elat, speed in edges_raw:
    u = node_to_id[round_coord(slon, slat)]
    v = node_to_id[round_coord(elon, elat)]
    if u == v:
        continue
    xu, yu = id_to_xy[u]
    xv, yv = id_to_xy[v]
    dist_m = np.sqrt((xu - xv)**2 + (yu - yv)**2)
    time_min = dist_m / (speed * 1000 / 60.0)
    edges_for_nx.append((u, v, time_min))

print(f"Total edge yang akan dimasukkan: {len(edges_for_nx)}")

# ----------------------------
# 6. MEMBANGUN GRAF
# ----------------------------
print("Membangun graf (NetworkX)...")
G = nx.Graph()
G.add_weighted_edges_from(edges_for_nx, weight='time_min')
print(f"Graf berhasil dibuat: {G.number_of_nodes()} simpul, {G.number_of_edges()} sisi")

del edges_raw, edges_for_nx, id_to_xy, x_arr, y_arr

# ----------------------------
# 7. CARI SIMPUL TERDEKAT DENGAN TITIK PUSAT
# ----------------------------
origin_lat, origin_lon = ORIGIN_POINT
# Bangun KDTree dengan koordinat asli (lon, lat)
tree = cKDTree(np.array(node_list))   # (lon, lat)
dist, idx = tree.query([origin_lon, origin_lat])   # untuk satu titik, idx scalar
origin_node = idx   # <-- PERBAIKAN: tidak perlu [0]
print(f"Node pusat: {origin_node} -> {node_list[origin_node]}")

# ----------------------------
# 8. HITUNG ISOCHRONE
# ----------------------------
print("Menghitung area jangkauan...")
def reachable_nodes(G, source, max_time):
    lengths = nx.single_source_dijkstra_path_length(
        G, source, cutoff=max_time, weight='time_min'
    )
    return set(lengths.keys())

iso_nodes = {}
for limit in TIME_LIMITS:
    start = time.time()
    nodes_set = reachable_nodes(G, origin_node, limit)
    iso_nodes[limit] = nodes_set
    print(f"  {limit} menit: {len(nodes_set)} simpul terjangkau "
          f"(selesai dalam {time.time()-start:.1f} detik)")

# ----------------------------
# 9. BUAT POLIGON UNTUK TIAP LAYER
# ----------------------------
def create_polygon_from_nodes(node_ids_set, node_list, node_to_xy_proj):
    if len(node_ids_set) < 3:
        return None
    points_proj = [Point(node_to_xy_proj[i]) for i in node_ids_set]
    mp = MultiPoint(points_proj)
    hull = mp.convex_hull
    if hull.geom_type == 'Polygon':
        return hull
    elif hull.geom_type == 'MultiPolygon':
        return max(hull.geoms, key=lambda a: a.area)
    else:
        return None

node_to_xy_proj = {i: transformer.transform(pt[0], pt[1]) for i, pt in enumerate(node_list)}

polygons = {}
for limit in sorted(TIME_LIMITS, reverse=True):
    hull_proj = create_polygon_from_nodes(iso_nodes[limit], node_list, node_to_xy_proj)
    if hull_proj is None:
        print(f"  {limit} menit: tidak bisa membentuk poligon")
        continue
    transformer_back = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    coords_lonlat = [transformer_back.transform(x, y) for x, y in hull_proj.exterior.coords]
    poly_4326 = Polygon(coords_lonlat)   # <-- Polygon sekarang tersedia
    polygons[limit] = poly_4326
    print(f"  {limit} menit: poligon berhasil dibuat")

# ----------------------------
# 10. VISUALISASI PETA HTML
# ----------------------------
print("Menyusun peta...")
m = folium.Map(location=ORIGIN_POINT, zoom_start=15, tiles='CartoDB positron')

color_map = dict(zip(sorted(TIME_LIMITS, reverse=True), COLORS[::-1]))
for limit, poly in polygons.items():
    gdf_poly = gpd.GeoDataFrame(index=[0], geometry=[poly], crs="EPSG:4326")
    folium.GeoJson(
        gdf_poly.__geo_interface__,
        style_function=lambda x, color=color_map[limit], limit=limit: {
            'fillColor': color,
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.3
        },
        name=f'{limit} menit'
    ).add_to(m)

folium.Marker(
    ORIGIN_POINT,
    popup='Titik Pusat',
    icon=folium.Icon(color='blue', icon='star')
).add_to(m)

folium.LayerControl().add_to(m)

# Tambahkan legenda kustom (HTML)
legend_html = '''
<div style="
    position: fixed;
    bottom: 50px; right: 50px;
    width: 130px;
    background-color: white;
    border:2px solid grey;
    z-index:9999;
    font-size:14px;
    padding: 10px;
    ">
    <b>Waktu Tempuh</b><br>
    <i style="background:green; width:18px; height:18px; display:inline-block;"></i> 5 menit<br>
    <i style="background:yellow; width:18px; height:18px; display:inline-block;"></i> 10 menit<br>
    <i style="background:orange; width:18px; height:18px; display:inline-block;"></i> 20 menit<br>
    <i style="background:red; width:18px; height:18px; display:inline-block;"></i> 30 menit<br>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

output_html = 'isochrone_polygon_map.html'
m.save(output_html)
print(f"\nPeta berhasil disimpan: {output_html}")