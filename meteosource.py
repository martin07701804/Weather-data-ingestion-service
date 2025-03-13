import requests

API_KEY = 'wt074jv7q1k5hh0j3wnicvxyqjudxrxrjbo7qmug'  
BASE_URL = "https://www.meteosource.com/api/v1/free/point"

# Seznam stanic (název a place_id)
stations = [
    {"name": "Prague", "place_id": "prague"},
    {"name": "Hlavní město Praha", "place_id": "hlavni-mesto-praha"},
    {"name": "Modřany", "place_id": "modrany"},
    {"name": "Libeň", "place_id": "liben"},
    {"name": "Černý Most", "place_id": "cerny-most"},
    {"name": "Braník", "place_id": "branik"},
    {"name": "Letňany", "place_id": "letnany"}
]

for station in stations:
    params = {
        'key': API_KEY,
        'place_id': station['place_id']
    }
    response = requests.get(BASE_URL, params=params)
    
    try:
        data = response.json()
    except Exception as e:
        print(f"Chyba při převodu odpovědi na JSON pro stanici {station['name']}: {e}")
        continue

    # Získání údajů o aktuálním počasí
    current = data.get('current', {})
    temperature = current.get('temperature', 'N/A')
    summary = current.get('summary', 'N/A')
    icon = current.get('icon', 'N/A')
    
    wind = current.get('wind', {})
    wind_speed = wind.get('speed', 'N/A')
    wind_dir = wind.get('dir', 'N/A')
    
    precipitation = current.get('precipitation', {})
    precip_total = precipitation.get('total', 'N/A')
    precip_type = precipitation.get('type', 'N/A')
    
    cloud_cover = current.get('cloud_cover', 'N/A')
    
    # Získání dalších údajů o stanici
    lat = data.get('lat', 'N/A')
    lon = data.get('lon', 'N/A')
    elevation = data.get('elevation', 'N/A')
    
    # Výpis všech údajů
    print(f"Stanice: {station['name']} ({station['place_id']})")
    print(f"  Souřadnice: {lat}, {lon}")
    print(f"  Nadmořská výška: {elevation} m")
    print(f"  Aktuální teplota: {temperature} °C")
    print(f"  Počasí: {summary} (ikona: {icon})")
    print(f"  Vítr: {wind_speed} m/s, směr: {wind_dir}")
    print(f"  Srážky: {precip_total} (typ: {precip_type})")
    print(f"  Oblačnost: {cloud_cover} %")
    print("-" * 40)
