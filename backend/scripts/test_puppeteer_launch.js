const puppeteer = require('../frontend/node_modules/puppeteer-core');

async function testLaunch() {
  const browser = await puppeteer.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  console.log('Browser launched successfully!');
  const page = await browser.newPage();
  await page.goto('http://localhost:5173');
  console.log('Navigated to http://localhost:5173. Title:', await page.title());
  await browser.close();
  console.log('Browser closed cleanly.');
}

testLaunch().catch(err => {
  console.error('Launch failed:', err);
  process.exit(1);
});
