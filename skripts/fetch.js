// skripts/fetch.js
import fs from "fs";
import path from "path";
import puppeteer from "puppeteer-extra";
import StealthPlugin from "puppeteer-extra-plugin-stealth";
import * as cheerio from "cheerio";

puppeteer.use(StealthPlugin());

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
  const title = $(container).find("h4.tide-day__date, h3").first().text().trim();
  const dm = title.match(/([A-Za-z]+day)\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/);
  if (!dm) return null;
  const [, , day, month, year] = dm;
  const dateISO = new Date(`${month} ${day}, ${year}`).toISOString().split("T")[0];

  const tides = [];
  $(container)
    .find("table.tide-day-tides tbody tr")
    .each((_, row) => {
      const tds = $(row).find("td");
      if (tds.length < 3) return;

      const typeText = $(tds[0]).text().trim();
      const timeText = $(tds[1]).text().trim();
      const heightText = $(tds[2]).text().trim();

      const typ = typeText.includes("High") ? "Hochwasser" : "Niedrigwasser";
      const hm = heightText.match(/(-?\d+(?:\.\d+)?)\s*m/);
      if (!hm) return;

      tides.push({
        zeit: to24h(timeText),
        typ,
        hoehe_m: parseFloat(hm[1])
      });
    });

  return tides.length ? { date: dateISO, tides } : null;
}

async function scrapeTides() {
  console.log("🌊 Lade Gezeiten …");

  const browser = await puppeteer.launch({
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-gpu"
    ]
  });

  const page = await browser.newPage();

  await page.setUserAgent(
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
      "AppleWebKit/537.36 (KHTML, like Gecko) " +
      "Chrome/122.0.0.0 Safari/537.36"
  );

  console.log("🔗 Öffne Seite:", URL);
  await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 90000 });

  // 🧩 Cookie-Banner automatisch akzeptieren
  try {
    await page.waitForSelector('button[mode="primary"], button[aria-label*="Accept"]', {
      timeout: 5000
    });
    await page.click('button[mode="primary"], button[aria-label*="Accept"]');
    console.log("🍪 Cookie-Dialog akzeptiert");
  } catch {
    console.log("✅ Kein Cookie-Dialog sichtbar");
  }

  // ⏳ Warten auf den Inhalt
  await page.waitForSelector(".tide-day, .tide-header-today", { timeout: 20000 });

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
    console.error("❌ Keine Gezeiten-Daten gefunden!");
    console.error("HTML-Vorschau (gekürzt):", html.slice(0, 500));
    throw new Error("Keine Gezeiten-Daten gefunden!");
  }

  const out = {
    meta: {
      location: "Playa del Inglés",
      timezone: "Atlantic/Canary",
      generatedAt: new Date().toISOString()
    },
    days
  };

  const outDir = path.resolve("data");
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, "latest.json");
  fs.writeFileSync(outFile, JSON.stringify(out, null, 2), "utf8");

  console.log(`✅ geschrieben: ${outFile} (Tage: ${days.length})`);
}

scrapeTides().catch((err) => {
  console.error("🚨 Fehler:", err.message);
  process.exit(1);
});
