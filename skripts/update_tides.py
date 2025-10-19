import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

# 🌍 URL der Quelle (Playa del Inglés)
URL = "https://www.tide-forecast.com/locations/Playa-del-Ingles-Canarias-Spain/tides/latest"


def scrape_tides():
    print("⏳ Lade Tide-Daten von:", URL)
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Tagesblöcke finden
    day_blocks = soup.select("div.tide-day")
    if not day_blocks:
        raise RuntimeError("⚠️ Keine Tagesdaten gefunden – Struktur evtl. geändert?")

    days_data = []

    for day_block in day_blocks:
        # Datum
        date_header = day_block.find("h3")
        if not date_header:
            continue

        date_text = date_header.get_text(strip=True)
        date_text = date_text.replace("Tide Times for Playa del Ingles:", "").strip()

        try:
            date_obj = datetime.strptime(date_text, "%A %d %B %Y")
        except ValueError:
            time_tag = day_block.find("time")
            if time_tag and time_tag.has_attr("datetime"):
                date_obj = datetime.strptime(time_tag["datetime"], "%Y-%m-%d")
            else:
                print(f"⚠️ Datum konnte nicht gelesen werden: {date_text}")
                continue

        day_data = {"date": date_obj.strftime("%Y-%m-%d"), "tides": []}

        # Alle Zeilen (Tide-Werte)
        rows = day_block.select("table.tide-day-tides tbody tr")

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            typ = cols[0].get_text(strip=True)
            zeit_text = cols[1].get_text(strip=True).split(" ")[0]

            # Zeit ins 24h-Format umwandeln
            try:
                zeit_obj = datetime.strptime(zeit_text, "%I:%M%p")
                zeit_str = zeit_obj.strftime("%H:%M")
            except ValueError:
                zeit_str = zeit_text  # Falls Format schon 24h ist

            # Höhe extrahieren
            height_tag = cols[2].find("b", class_="js-two-units-length-value_primary")
            if not height_tag:
                continue

            hoehe_text = height_tag.get_text(strip=True)
            hoehe_text = (
                hoehe_text.replace("m", "")
                .replace("−", "-")  # Unicode-Minus in normales Minus umwandeln
                .strip()
            )

            # Float konvertieren, inkl. negativer Werte und "0.0"
            try:
                hoehe_m = float(hoehe_text)
            except ValueError:
                print(f"⚠️ Ungültiger Höhenwert übersprungen: '{hoehe_text}'")
                continue

            # Typ übersetzen
            if "High" in typ:
                typ_de = "Hochwasser"
            elif "Low" in typ:
                typ_de = "Niedrigwasser"
            else:
                typ_de = typ

            # Wert speichern
            day_data["tides"].append(
                {"zeit": zeit_str, "typ": typ_de, "hoehe_m": hoehe_m}
            )

        if day_data["tides"]:
            days_data.append(day_data)

    final_data = {
        "meta": {
            "location": "Playa del Inglés",
            "timezone": "Atlantic/Canary",
            "generatedAt": datetime.utcnow().isoformat(),
        },
        "days": days_data,
    }

    print(f"✅ {len(days_data)} Tage erfolgreich geladen.")
    return final_data


def save_json(data, path="data/latest.json"):
    import os

    os.makedirs("data", exist_ok=True)  # Ordner sicherstellen
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Datei gespeichert: {path}")


if __name__ == "__main__":
    try:
        data = scrape_tides()
        save_json(data)
    except Exception as e:
        print("❌ Fehler beim Abrufen der Daten:", e)
