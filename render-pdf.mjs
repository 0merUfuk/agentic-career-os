import puppeteer from 'puppeteer-core';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const [inputArg, outputArg] = process.argv.slice(2);
if (!inputArg || !outputArg) {
  console.error('Usage: node render-pdf.mjs <input.html> <output.pdf>');
  process.exit(1);
}

const htmlPath = path.resolve(process.cwd(), inputArg);
const pdfPath = path.resolve(process.cwd(), outputArg);

if (!fs.existsSync(htmlPath)) {
  console.error(`Input not found: ${htmlPath}`);
  process.exit(1);
}

fs.mkdirSync(path.dirname(pdfPath), { recursive: true });

const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: true,
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});

const page = await browser.newPage();
await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0' });
await page.pdf({
  path: pdfPath,
  format: 'Letter',
  printBackground: true,
  displayHeaderFooter: false,
  margin: { top: '0.8in', bottom: '0.8in', left: '0.8in', right: '0.8in' },
});
await page.close();
await browser.close();
console.log(`Rendered ${pdfPath}`);
