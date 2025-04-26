import os
import time
import requests
import numpy as np
import folium
from tabulate import tabulate

def get_forecast_for_point(lat, lon):
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relativehumidity_2m,dewpoint_2m,precipitation,windspeed_10m,weathercode",
        "timezone": "Europe/Prague"
    }
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        print(f"Chyba při získávání dat pro ({lat}, {lon}): {response.status_code}")
        return None
    data = response.json()
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return None
    index = 0  # vezmeme data pro první časový okamžik
    return {
        "lat": lat,
        "lon": lon,
        "time": times[index],
        "temperature": hourly.get("temperature_2m", [None])[index],
        "humidity": hourly.get("relativehumidity_2m", [None])[index],
        "dewpoint": hourly.get("dewpoint_2m", [None])[index],
        "precipitation": hourly.get("precipitation", [None])[index],
        "windspeed": hourly.get("windspeed_10m", [None])[index],
        "weathercode": hourly.get("weathercode", [None])[index]
    }

def get_forecast_grid():
    # Definujeme rozsah – např. latitude 50.05 až 50.10 a longitude 14.35 až 14.55
    lats = np.linspace(50.05, 50.10, 10)
    lons = np.linspace(14.35, 14.55, 10)
    
    results = []
    for lat in lats:
        for lon in lons:
            forecast = get_forecast_for_point(lat, lon)
            if forecast:
                results.append(forecast)
            time.sleep(0.2)  # malá pauza, abychom API nezahltili
    return results

def create_table(forecasts):
    table = []
    # Seznamy pro průměry
    temps, hums, dewp, precs, winds = [], [], [], [], []
    
    for fc in forecasts:
        # Uložíme hodnoty do příslušných seznamů
        if fc["temperature"] is not None:
            temps.append(fc["temperature"])
        if fc["humidity"] is not None:
            hums.append(fc["humidity"])
        if fc["dewpoint"] is not None:
            dewp.append(fc["dewpoint"])
        if fc["precipitation"] is not None:
            precs.append(fc["precipitation"])
        if fc["windspeed"] is not None:
            winds.append(fc["windspeed"])
        
        row = [
            fc["lat"],
            fc["lon"],
            fc["time"],
            f"{fc['temperature']:.1f}" if fc["temperature"] is not None else "N/A",
            f"{fc['humidity']}" if fc["humidity"] is not None else "N/A",
            f"{fc['dewpoint']:.1f}" if fc["dewpoint"] is not None else "N/A",
            f"{fc['precipitation']:.1f}" if fc["precipitation"] is not None else "N/A",
            f"{fc['windspeed']:.1f}" if fc["windspeed"] is not None else "N/A",
            f"{fc['weathercode']}" if fc["weathercode"] is not None else "N/A"
        ]
        table.append(row)
    
    # Vypočítáme průměry
    avg_temp = np.mean(temps) if temps else None
    avg_hum = np.mean(hums) if hums else None
    avg_dewp = np.mean(dewp) if dewp else None
    avg_prec = np.mean(precs) if precs else None
    avg_wind = np.mean(winds) if winds else None
    
    avg_row = [
        "PRŮMĚR",
        "",
        "",
        f"{avg_temp:.1f}" if avg_temp is not None else "N/A",
        f"{avg_hum:.1f}" if avg_hum is not None else "N/A",
        f"{avg_dewp:.1f}" if avg_dewp is not None else "N/A",
        f"{avg_prec:.1f}" if avg_prec is not None else "N/A",
        f"{avg_wind:.1f}" if avg_wind is not None else "N/A",
        ""
    ]
    table.append(avg_row)
    
    headers = [
        "Latitude", "Longitude", "Čas", "Teplota (°C)",
        "Vlhkost (%)", "Rosný bod (°C)", "Srážky (mm)",
        "Vítr (km/h)", "Weather code"
    ]
    
    return tabulate(table, headers=headers, tablefmt="fancy_grid")

def create_map(forecasts):
    # Nastavíme centrální bod mapy (například střed Prahy)
    map_center = [50.0755, 14.4378]
    prague_map = folium.Map(location=map_center, zoom_start=12)
    
    # Přidáme body z forecasts
    for fc in forecasts:
        popup_text = (
            f"Lat: {fc['lat']:.4f}, Lon: {fc['lon']:.4f}<br>"
            f"Teplota: {fc['temperature']:.1f} °C<br>"
            f"Vlhkost: {fc['humidity']} %"
        )
        folium.Marker(
            location=[fc['lat'], fc['lon']],
            popup=popup_text,
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(prague_map)
    
    return prague_map

def main():
    forecasts = get_forecast_grid()
    
    # Vytvoření a uložení tabulky
    table_str = create_table(forecasts)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    table_file_path = os.path.join(script_dir, "tabulka_grid.txt")
    try:
        with open(table_file_path, "w", encoding="utf-8") as f:
            f.write(table_str)
        print(f"Tabulka byla úspěšně uložena do souboru: {table_file_path}")
    except Exception as e:
        print("Nepodařilo se uložit tabulku:", e)
    
    # Vytvoření a uložení mapy
    prague_map = create_map(forecasts)
    map_file_path = os.path.join(script_dir, "mapa.html")
    try:
        prague_map.save(map_file_path)
        print(f"Mapa byla úspěšně uložena do souboru: {map_file_path}")
    except Exception as e:
        print("Nepodařilo se uložit mapu:", e)

if __name__ == "__main__":
    main()
