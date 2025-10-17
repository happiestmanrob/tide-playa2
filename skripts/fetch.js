// scripts/fetch.js
import fs from "fs";
import path from "path";
import puppeteer from "puppeteer";
import * as cheerio from "cheerio";

const URL = "https://www.tide-forecast.com/locations/Playa-del-Ingles/tides/latest";

async function scrapeTides() {
  console.log("🌊 Lade Gezeiten für Playa del Inglés ...");
  console.log("🔗 URL:", URL);

  const browser = await puppeteer.launch({
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox"]
  });

  const page = await browser.newPage();
  await page.goto(URL, { waitUntil: "networkidle2", timeout: 60000 });
  await page.waitForSelector(".tide-header-today, .tide-day", { timeout: 30000 });

  const html = await page.content();
  await browser.close();

  const $ = cheerio.load(html);
  const days = [];

  // 🔹 Heute (explizit eigener Block)
  const todayBlock = $(".tide-header-today");
  if (todayBlock.length) {
    const todayData = extractToday(todayBlock, $);
    if (todayData) {
      days.push(todayData);
      console.log(`📅 ${todayData.date}: ${todayData.tides.length} Einträge (heute)`);
    }
  }

  // 🔹 Zukünftige Tage (alle .tide-day-Container)
  $(".tide-day").each((_, el) => {
    const data = extractDay($(el), $);
    if (data) {
      days.push(data);
      console.log(`📅 ${data.date}: ${data.tides.length} Einträge`);
    }
  });

  if (!days.length) throw new Error("❌ Keine Gezeiten-Daten gefunden!");

  const result = {
    meta: {
      location: "Playa del Inglés",
      timezone: "Atlantic/Canary",
      generatedAt: new Date().toISOString()
    },
    days
  };

  const outputDir = path.resolve("public/data");
  if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

  const outputFile = path.join(outputDir, "latest.json");
  fs.writeFileSync(outputFile, JSON.stringify(result, null, 2), "utf8");

  console.log(`✅ Erfolgreich geschrieben: ${outputFile} (${days.length} Tage)`);
}

// 🔧 Heute-Block extrahieren
function extractToday(block, $) {
  const title = block.find("h3").text().trim();
  const dateMatch = title.match(/([A-Za-z]+day)\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/);
  if (!dateMatch) return null;

  const [, , day, month, year] = dateMatch;
  const dateISO = new Date(`${month} ${day}, ${year}`).toISOString().split("T")[0];

  const tides = [];
  block.find("table.tide-day-tides tbody tr").each((_, row) => {
    const cols = $(row).find("td");
    if (cols.length < 3) return;

    const typeText = $(cols[0]).text().trim();
    const timeText = $(cols[1]).find("b").first().text().trim();
    const heightText = $(cols[2]).text().trim();

    if (!typeText || !timeText || !heightText) return;

    const typ = typeText.includes("High") ? "Hochwasser" : "Niedrigwasser";
    const meterMatch = heightText.match(/([\d.]+)\s*m/);
    const hoehe_m = meterMatch ? parseFloat(meterMatch[1]) : null;
    if (!hoehe_m) return;

    tides.push({
      zeit: convertTo24h(timeText),
      typ,
      hoehe_m
    });
  });

  return tides.length ? { date: dateISO, tides } : null;
}

// 🔧 Zukünftige Tage extrahieren
function extractDay(block, $) {
  const title = block.find("h4.tide-day__date").text().trim();
  const dateMatch = title.match(/([A-Za-z]+day)\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/);
  if (!dateMatch) return null;

  const [, , day, month, year] = dateMatch;
  const dateISO = new Date(`${month} ${day}, ${year}`).toISOString().split("T")[0];

  const tides = [];
  block.find("table.tide-day-tides tbody tr").each((_, row) => {
    const cols = $(row).find("td");
    if (cols.length < 3) return;

    const typeText = $(cols[0]).text().trim();
    const timeText = $(cols[1]).find("b").first().text().trim();
    const heightText = $(cols[2]).text().trim();

    if (!typeText || !timeText || !heightText) return;

    const typ = typeText.includes("High") ? "Hochwasser" : "Niedrigwasser";
    const meterMatch = heightText.match(/([\d.]+)\s*m/);
    const hoehe_m = meterMatch ? parseFloat(meterMatch[1]) : null;
    if (!hoehe_m) return;

    tides.push({
      zeit: convertTo24h(timeText),
      typ,
      hoehe_m
    });
  });

  return tides.length ? { date: dateISO, tides } : null;
}

// 🕒 Zeit ins 24h-Format konvertieren
function convertTo24h(timeStr) {
  const match = timeStr.match(/(\d{1,2}):(\d{2})\s*(AM|PM)?/i);
  if (!match) return timeStr;
  let [_, h, m, ap] = match;
  let hour = parseInt(h, 10);
  const minute = m.padStart(2, "0");
  if (ap) {
    ap = ap.toUpperCase();
    if (ap === "PM" && hour < 12) hour += 12;
    if (ap === "AM" && hour === 12) hour = 0;
  }
  return `${String(hour).padStart(2, "0")}:${minute}`;
}

scrapeTides().catch((err) => {
  console.error("🚨 Fehler:", err.message);
  process.exit(1);
});
