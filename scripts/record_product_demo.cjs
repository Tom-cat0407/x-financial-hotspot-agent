const { chromium } = require('../frontend/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const demoDir = path.join(root, 'outputs', 'demo');
const segments = JSON.parse(fs.readFileSync(path.join(demoDir, 'product_segments.json'), 'utf8'));

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 960 },
    recordVideo: { dir: demoDir, size: { width: 1440, height: 960 } },
  });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  for (const segment of segments) {
    await page.goto(`http://127.0.0.1:8000/outputs/demo/product_story.html?slide=${segment.slide}`, { waitUntil: 'networkidle' });
    await sleep(Number(segment.seconds) * 1000);
  }
  await context.close();
  await browser.close();
  const videos = fs.readdirSync(demoDir)
    .filter(name => name.endsWith('.webm'))
    .map(name => path.join(demoDir, name))
    .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  if (!videos[0]) throw new Error('No video was generated');
  const target = path.join(demoDir, 'product_demo_silent.webm');
  if (fs.existsSync(target)) fs.unlinkSync(target);
  fs.renameSync(videos[0], target);
  console.log(target);
})();
