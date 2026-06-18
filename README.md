# UAE Traffic Mobility Isochrone Map

## 📌 Project Overview
As a Data Scientist/Analyst working with spatial and mobility data, understanding the reachability of a specific location within a given timeframe is crucial. This project generates an **Isochrone Map** based on actual traffic mobility data in the United Arab Emirates (UAE). 

An isochrone map displays areas that are accessible from a specific point of origin within a specific time threshold. In this project, we calculate the coverage areas for **5, 10, 20, and 30 minutes** of travel time.

### 🎯 Key Use Cases
- **Logistics & Supply Chain:** Optimizing warehouse locations and estimating last-mile delivery coverage.
- **Urban Planning:** Analyzing the accessibility of public facilities, hospitals, or commercial centers based on real-world traffic conditions.
- **Retail Expansion:** Determining the target audience within a certain driving radius from a potential new store location.
- **Emergency Services:** Estimating the response time radius for ambulances and fire trucks.

---

## 🛠️ Methodology & Technical Stack

The script (`isochrone_map.py`) follows a robust data engineering and spatial analysis pipeline:

1. **Data Parsing & Cleaning (`Pandas`, `GeoPandas`):** 
   Reads the traffic dataset, parses the Well-Known Text (WKT) LineString geometries, and filters out invalid speed records.
2. **Graph Network Construction (`NetworkX`):** 
   Extracts unique coordinate nodes and edges from the geometries. Calculates the travel time for each road segment based on distance and average speed, then builds a weighted graph where the weights are travel times in minutes.
3. **Isochrone Calculation (Dijkstra's Algorithm):** 
   Uses a KD-Tree (`SciPy`) to snap the origin coordinate to the nearest graph node, then runs Dijkstra's algorithm to find all nodes reachable within the defined time limits (5, 10, 20, 30 minutes).
4. **Spatial Polygon Generation (`Shapely`, `PyProj`):** 
   Projects coordinates to EPSG:3857 (meters) for accurate spatial operations, computes Convex Hulls around the reachable nodes to create continuous polygons, and projects them back to EPSG:4326 (Lat/Lon).
5. **Interactive Visualization (`Folium`):** 
   Renders an interactive HTML map (`isochrone_polygon_map.html`) displaying the layered isochrone polygons with a custom legend.

---

## 🚀 How to Run

### 1. Prerequisites
Ensure you have Python installed, then install the required libraries:

```bash
pip install pandas geopandas shapely networkx folium numpy pyproj scipy
```

### 2. Dataset
**Note:** The dataset (`traffic_data.csv`) is **strictly confidential** and is therefore not included in this repository. 

To run this script on your own data, ensure your CSV file has at least the following columns:
- `geometry`: The road segment geometry in WKT (Well-Known Text) format (e.g., `LINESTRING (lon lat, lon lat)`).
- `average_speed_kmh`: The average historical or real-time speed on that road segment.

### 3. Execution
Run the script via your terminal:

```bash
python isochrone_map.py
```

### 4. Output
The script will output an interactive map file named `isochrone_polygon_map.html`. Open this file in any web browser to explore the isochrone areas.

---

## 🔒 Confidentiality Notice
The `.gitignore` is configured to ignore `traffic_data.csv` (and any other `.csv` or `.parquet` data files) to prevent accidental uploads of proprietary mobility data to GitHub.
