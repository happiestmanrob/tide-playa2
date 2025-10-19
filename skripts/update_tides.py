import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import sys

# 🌍 URL der Quelle
BASE_URL = "https://www.tide-forecast.com/locations/Playa-del-Ingles-Canarias-Spain"
URLS = [
    f"{BASE_URL}/tides/latest",
    f"{BASE_URL}/tides"
]

def fetch_html():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TideBot/1.0; +https://github.com/happiestmanrob/tide-playa)"}
    for url in URLS:
        print(f"🌐 Versuche, Daten von {url} zu laden …")
        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            if "Tide Times" in r.text or "Hochwasser" in r.text or "Low Tide" in r.text:
                print(f"✅ Erfolgreich geladen: {url}")
                return r.text
        except requests.HTTPError as e:
            print(f"⚠️ Fehler ({url}): {e}")
        except Exception as e:
            print(f"❌ Unerwarteter Fehler bei {url}: {e}")
    raise RuntimeError("Keine gültige Tide-Seite gefunden oder HTML-Struktur geändert.")

def parse_tides(html):
    soup = BeautifulSoup(html, "html.parser")
    day_blocks = soup.select("div.tide-day")

    if not day_blocks:
        raise RuntimeError("⚠️ Keine <div class='tide-day'>-Blöcke gefunden — Struktur geändert?")

    days_data = []

    for day_block in day_blocks:
        # Datum finden
        date_header = day_block.find("h3")
        if not date_header:
            continue

        date_text = date_header.get_text(strip=True)
        date_obj = None

        for fmt in ["%A %d %B %Y", "%A %d %b %Y"]:
            try:
                date_obj = datetime.strptime(date_text.replace("Tide Times for Playa del Ingles:", "").strip(), fmt)
                break
            except ValueError:
                continue

        if not date_obj:
            time_tag = day_block.find("time")
            if time_tag and time_tag.has_attr("datetime"):
                try:
                    date_obj = datetime.strptime(time_tag["datetime"], "%Y-%m-%d")
                except ValueError:
                    pass

        if not date_obj:
            print(f"⚠️ Kein gültiges Datum erkannt in: {date_text}")
            continue

        day_data = {"date": date_obj.strftime("%Y-%m-%d"), "tides": []}

        # Tabelle auslesen
        rows = day_block.select("table.tide-day-tides tbody tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            typ = cols[0].get_text(strip=True)
            zeit_raw = cols[1].get_text(strip=True).split(" ")[0]
            height_tag = cols[2].find("b", class_="js-two-units-length-value_primary")

            if not height_tag:
                continue

            try:
                zeit_obj = datetime.strptime(zeit_raw, "%I:%M%p")
                zeit_str = zeit_obj.strftime("%H:%M")
            except ValueError:
                zeit_str = zeit_raw

            try:
                hoehe_m = float(height_tag.get_text(strip=True).replace("m", "").strip())
            except ValueError:
                hoehe_m = None

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

    if not days_data:
        raise RuntimeError("⚠️ Keine Gezeitendaten extrahiert.")

    return {
        "meta": {
            "location": "Playa del Inglés",
            "timezone": "Atlantic/Canary",
            "source": BASE_URL,
            "generatedAt": datetime.utcnow().isoformat() + "Z"
        },
        "days": days_data
    }

def save_json(data, path="data/latest.json"):
    import os
    os.makedirs("data", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON-Datei gespeichert unter: {path}")

if __name__ == "__main__":
    try:
        html = fetch_html()
        data = parse_tides(html)
        save_json(data)
        print("🎉 Fertig! Gezeiten erfolgreich aktualisiert.")
    except Exception as e:
        print(f"❌ Fehler beim Scrapen: {e}")
        sys.exit(1)
