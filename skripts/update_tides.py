# skripts/update_tides.py
import re
import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Eine valide Basis-URL reicht – keine Verdopplungen mehr
BASE_URL = "https://www.tide-forecast.com/locations/Playa-del-Ingles/tides/latest"

def fetch_html(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

def to_24h(s: str) -> str:
    # akzeptiert "6:39 PM", "00:12 AM", auch "06:17"
    m = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM)?", s, re.I)
    if not m:
        return s.strip()
    h, mnt, ap = m.group(1), m.group(2), m.group(3)
    h = int(h)
    if ap:
        ap = ap.upper()
        if ap == "PM" and h < 12: h += 12
        if ap == "AM" and h == 12: h = 0
    return f"{h:02d}:{mnt}"

def parse_date(text: str) -> str | None:
    # z. B. "Wednesday 05 November 2025"
    m = re.search(r"([A-Za-z]+day)\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text)
    if not m:
        return None
    day, month, year = m.group(2), m.group(3), m.group(4)
    return datetime.strptime(f"{day} {month} {year}", "%d %B %Y").strftime("%Y-%m-%d")

def parse_day(container: BeautifulSoup) -> dict | None:
    # Versuche Datum an mehreren Stellen
    date_iso = None
    h4 = container.find("h4", class_="tide-day__date")
    if h4:
        date_iso = parse_date(h4.get_text(" ", strip=True))
    if not date_iso:
        h3 = container.find("h3")
        if h3:
            date_iso = parse_date(h3.get_text(" ", strip=True))
    if not date_iso:
        time_tag = container.find("time")
        if time_tag and time_tag.has_attr("datetime"):
            date_iso = time_tag["datetime"]

    if not date_iso:
        return None

    tides = []
    for row in container.select("table.tide-day-tides tbody tr"):
        tds = row.find_all("td")
        if len(tds) < 3:
            continue

        typ_raw = tds[0].get_text(" ", strip=True)
        time_raw = tds[1].get_text(" ", strip=True)
        # Höhe steht im <b class="js-two-units-length-value__primary">
        b = tds[2].find("b", class_="js-two-units-length-value__primary")
        height_raw = (b.get_text(" ", strip=True) if b else tds[2].get_text(" ", strip=True))

        # Typ übersetzen anhand des Textes (nicht über Schwellenwerte!)
        if "High" in typ_raw:
            typ_de = "Hochwasser"
        elif "Low" in typ_raw:
            typ_de = "Niedrigwasser"
        else:
            continue

        # Zeit nach 24h
        zeit = to_24h(time_raw)

        # Zahl inkl. Minus und 0.0 extrahieren
        m = re.search(r"(-?\d+(?:\.\d+)?)\s*m", height_raw)
        if not m:
            continue
        hoehe_m = float(m.group(1))   # kann negativ oder 0.0 sein

        tides.append({
            "zeit": zeit,
            "typ": typ_de,
            "hoehe_m": hoehe_m
        })

    if not tides:
        return None

    return {"date": date_iso, "tides": tides}

def scrape() -> dict:
    html = fetch_html(BASE_URL)
    soup = BeautifulSoup(html, "html.parser")

    # Heute und kommende Tage abdecken
    blocks = []
    blocks += soup.select("div.tide-header-today")   # heute
    blocks += soup.select("div.tide-day")            # weitere Tage

    days = []
    for box in blocks:
        day = parse_day(box)
        if day:
            days.append(day)

    if not days:
        raise RuntimeError("Keine Tagesblöcke mit Gezeiten gefunden (Seitenstruktur geändert?).")

    # Nach Datum sortieren & Duplikate (falls heute doppelt) zusammenführen
    by_date = {}
    for d in days:
        by_date.setdefault(d["date"], []).extend(d["tides"])
    days = [{"date": k, "tides": v} for k, v in sorted(by_date.items(), key=lambda x: x[0])]

    return {
        "meta": {
            "location": "Playa del Inglés",
            "timezone": "Atlantic/Canary",
            "generatedAt": datetime.utcnow().isoformat()
        },
        "days": days
    }

def save_json(data: dict, path: str = "data/latest.json") -> None:
    from pathlib import Path
    Path("data").mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ geschrieben: {path}  (Tage: {len(data.get('days', []))})")

if __name__ == "__main__":
    data = scrape()
    save_json(data)
