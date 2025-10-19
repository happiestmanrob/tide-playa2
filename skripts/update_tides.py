import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

# 🌍 URL der Quelle (du kannst bei Bedarf andere Orte eintragen)
URL = "https://www.tide-forecast.com/locations/Playa-del-Ingles-Canarias-Spain/tides/latest"

# 🌊 Funktion: HTML abrufen und Gezeiten extrahieren
def scrape_tides():
    print("⏳ Lade Tide-Daten von:", URL)
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Alle Tagesblöcke finden
    day_blocks = soup.select("div.tide-day")
    if not day_blocks:
        raise RuntimeError("⚠️ Keine Tagesdaten gefunden – Struktur evtl. geändert?")

    days_data = []

    for day_block in day_blocks:
        # Datum extrahieren
        date_header = day_block.find("h3")
        if not date_header:
            continue

        date_text = date_header.get_text(strip=True)
        # Beispiel: "Wednesday 05 November 2025"
        try:
            date_obj = datetime.strptime(date_text.replace("Tide Times for Playa del Ingles:", "").strip(), 
                                         "%A %d %B %Y")
        except:
            # Alternativ: Suche nach <time datetime="2025-11-05">
            time_tag = day_block.find("time")
            if time_tag and time_tag.has_attr("datetime"):
                date_obj = datetime.strptime(time_tag["datetime"], "%Y-%m-%d")
            else:
                continue

        day_data = {
            "date": date_obj.strftime("%Y-%m-%d"),
            "tides": []
        }

        # Tabellenzeilen für diesen Tag
        rows = day_block.select("table.tide-day-tides tbody tr")

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            # Typ (High Tide / Low Tide)
            typ = cols[0].get_text(strip=True)
            if not typ:
                continue

            # Zeit extrahieren (z. B. 6:39 PM → 18:39)
            zeit_raw = cols[1].get_text(strip=True).split(" ")[0]
            try:
                zeit_obj = datetime.strptime(zeit_raw, "%I:%M%p")
                zeit_str = zeit_obj.strftime("%H:%M")
            except ValueError:
                zeit_str = zeit_raw  # Fallback

            # Höhe in Metern extrahieren
            height_tag = cols[2].find("b", class_="js-two-units-length-value_primary")
            if not height_tag:
                continue
            hoehe_text = height_tag.get_text(strip=True).replace("m", "").strip()
            try:
                hoehe_m = float(hoehe_text)
            except:
                hoehe_m = None

            # Übersetze Typ
            if "High" in typ:
                typ_de = "Hochwasser"
            elif "Low" in typ:
                typ_de = "Niedrigwasser"
            else:
                typ_de = typ

            if hoehe_m is not None:
                day_data["tides"].append({
                    "zeit": zeit_str,
                    "typ": typ_de,
                    "hoehe_m": hoehe_m
                })

        if day_data["tides"]:
            days_data.append(day_data)

    # JSON-Struktur
    final_data = {
        "meta": {
            "location": "Playa del Inglés",
            "timezone": "Atlantic/Canary",
            "generatedAt": datetime.utcnow().isoformat()
        },
        "days": days_data
    }

    return final_data

# 💾 JSON speichern
def save_json(data, path="data/latest.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Datei aktualisiert: {path}")

if __name__ == "__main__":
    try:
        data = scrape_tides()
        save_json(data)
    except Exception as e:
        print("❌ Fehler:", e)
