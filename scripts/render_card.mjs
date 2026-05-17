import { pathToFileURL } from "node:url";

async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch {
    try {
      return await import("../frontend/node_modules/playwright/index.mjs");
    } catch {
      return null;
    }
  }
}

const [htmlPath, pngPath, widthArg, heightArg] = process.argv.slice(2);
const playwright = await loadPlaywright();
if (!playwright || !htmlPath || !pngPath) {
  process.exit(2);
}

const browser = await playwright.chromium.launch({ headless: true });
try {
  const width = Number.parseInt(widthArg || "1600", 10);
  const height = Number.parseInt(heightArg || "900", 10);
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "networkidle" });
  await page.screenshot({ path: pngPath, fullPage: false });
} finally {
  await browser.close();
}
