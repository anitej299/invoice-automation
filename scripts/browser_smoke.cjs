// Optional browser smoke test: npm install --no-save playwright, then node scripts/browser_smoke.cjs.
// Uses a fresh Edge context and reads only this project's generated local demo credentials.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const env = Object.fromEntries(fs.readFileSync(path.join(root, '.env'), 'utf8').split(/\r?\n/).filter(l => l.includes('=')).map(l => [l.slice(0,l.indexOf('=')),l.slice(l.indexOf('=')+1)]));
(async () => {
  const browser = await chromium.launch({channel: 'msedge', headless: true});
  const page = await browser.newPage({viewport: {width: 1440, height: 1000}, timezoneId: 'Asia/Kolkata'});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto(process.env.APP_URL || 'http://127.0.0.1:5173');
    await page.getByLabel('Email address').fill(env.SEED_ADMIN_EMAIL);
    await page.getByLabel('Password', {exact: true}).fill(env.SEED_ADMIN_PASSWORD);
    await page.getByRole('button', {name: 'Sign in to workspace'}).click();
    await page.getByRole('heading', {name: 'Every invoice. In focus.'}).waitFor();
    await page.getByRole('heading', {name: 'Invoice value', exact: true}).waitFor();
    const output = path.join(root, 'docs/screenshots'); fs.mkdirSync(output, {recursive: true});
    await page.screenshot({path: path.join(output, 'dashboard.png'), fullPage: true, animations: 'disabled'});
    await page.getByRole('link', {name: 'Invoices', exact: true}).click();
    await page.getByRole('link', {name: 'DEMO-008', exact: true}).click();
    await page.getByText('Invoice total does not match subtotal + tax - discount', {exact: true}).first().waitFor();
    if (await page.getByRole('button', {name: 'Approve invoice'}).isEnabled()) throw new Error('Invalid invoice approval was enabled');
    await page.screenshot({path: path.join(output, 'invoice-review.png'), fullPage: true, animations: 'disabled'});
    await page.getByRole('link', {name: 'Vendors', exact: true}).click();
    await page.getByRole('cell', {name: 'Northstar Design', exact: true}).waitFor();
    await page.getByRole('link', {name: 'Audit logs', exact: true}).click();
    await page.getByRole('columnheader', {name: 'Performed by'}).waitFor();
    await page.setViewportSize({width: 390, height: 844});
    await page.getByRole('link', {name: 'Overview', exact: true}).click();
    await page.getByRole('heading', {name: 'Invoice value', exact: true}).waitFor();
    await page.screenshot({path: path.join(output, 'mobile.png'), fullPage: true, animations: 'disabled'});
    if (errors.length) throw new Error(errors.join('\n'));
    console.log('Browser smoke passed: login, dashboard, invoice review gate, vendors, audit, mobile; no page errors.');
  } finally { await browser.close(); }
})().catch(error => {console.error(error.message);process.exitCode=1;});
