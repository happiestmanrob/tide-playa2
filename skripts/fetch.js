// skripts/fetch.js
import fs from "fs";
import path from "path";
import puppeteer from "puppeteer";
import * as cheerio from "cheerio";

const URL = "https://www.tide-forecast.com/locations/Playa-del-Ingles/tides/latest";

function to24h(s) {
  const m = s.match(/(\d{1,2}):(\d{2})\s*(AM|PM)?/i);
  if (!m) return s.trim();
  let [_, h, min, ap] = m;
  let hour = parseInt(h, 10);
  if (ap) {
    ap = ap.toUpperCase();
    if (ap === "PM" && hour < 12) hour += 12;
    if (ap === "AM" && hour === 12) hour = 0;
  }
  return `${String(hour).padStart(2, "0")}:${min}`;
}

function parseDay($, container) {
  // Datum finden
  let dateISO = null;
  const titleH4 = $(container).find("h4.tide-day__date").first().text().trim();
  const titleH3 = $(container).find("h3").first().text().trim();
  const title = titleH4 || titleH3;

  const dm = title.match(/([A-Za-z]+day)\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/);
  if (dm) {
    const [, , day, month, year] = dm;
    dateISO = new Date(`${month} ${day}, ${year}`).toISOString().split("T")[0];
  } else {
    const tm = $(container).find("time[datetime]").attr("datetime");
    if (tm) dateISO = tm;
  }
  if (!dateISO) return null;

  const tides = [];
  $(container)
    .find("table.tide-day-tides tbody tr")
    .each((_, row) => {
      const tds = $(row).find("td");
      if (tds.length < 3) return;

      const typeText = $(tds[0]).text().trim();
      const timeText = $(tds[1]).text().trim();
      const b = $(tds[2]).find("b.js-two-units-length-value__primary").first();
      const heightText = (b.length ? b.text() : $(tds[2]).text()).trim();

      const typ =
        typeText.includes("High") ? "Hochwasser" :
        typeText.includes("Low") ? "Niedrigwasser" : null;
      if (!typ) return;

      const zeit = to24h(timeText);
      const hm = heightText.match(/(-?\d+(?:\.\d+)?)\s*m/);
      if (!hm) return;
      const hoehe_m = parseFloat(hm[1]);

      tides.push({ zeit, typ, hoehe_m });
    });

  if (!tides.length) return null;
  return { date: dateISO, tides };
}

async function scrapeTides() {
  console.log("🌊 Lade Gezeiten …");

  const browser = await puppeteer.launch({
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-gpu",
      "--single-process"
    ]
  });

  const page = await browser.newPage();

  await page.setUserAgent(
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
    "AppleWebKit/537.36 (KHTML, like Gecko) " +
    "Chrome/122.0.0.0 Safari/537.36"
  );

  await page.setViewport({ width: 1366, height: 900 });

  console.log("🔗 Öffne Seite:", URL);
  await page.goto(URL, { waitUntil: "networkidle2", timeout: 90000 });

  // ⏳ Warte auf vollständiges Rendering (kompatibel mit allen Puppeteer-Versionen)
  await new Promise(r => setTimeout(r, 5000));

  const html = await page.content();
  await browser.close();

  const $ = cheerio.load(html);
  const days = [];

  $(".tide-header-today, .tide-day").each((_, el) => {
    const d = parseDay($, el);
    if (d) {
      days.push(d);
      console.log(`📅 ${d.date}: ${d.tides.length} Einträge`);
    }
  });

  if (!days.length) {
    console.error("⚠️ Kein .tide-day-Container gefunden. Möglicherweise blockiert die Seite Headless-Zugriffe.");
    console.error("HTML-Vorschau (gekürzt):", html.slice(0, 400));
    throw new Error("Keine Gezeiten-Daten gefunden!");
  }

  const out = {
    meta: {
      location: "Playa del Inglés",
      timezone: "Atlantic/Canary",
      generatedAt: new Date().toISOString()
    },
    days: days
  };

  const outDir = path.resolve("data");
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, "latest.json");
  fs.writeFileSync(outFile, JSON.stringify(out, null, 2), "utf8");
  console.log(`✅ geschrieben: ${outFile} (Tage: ${days.length})`);
}

scrapeTides().catch((e) => {
  console.error("🚨 Fehler:", e.message);
  process.exit(1);
});
