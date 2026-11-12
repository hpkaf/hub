// 用 CDP 做真实移动端视口截图（Chrome headless CLI 的 --window-size 有 500px 下限）
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync } from 'node:fs';

const [,, url, out, W = '390', H = '844', DPR = '2'] = process.argv;
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PROFILE = new URL('../.cache/chrome-automation/profile-mobile', import.meta.url).pathname;
mkdirSync(PROFILE, { recursive: true });
const PORT = 9333;
const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${PROFILE}`, '--no-first-run', '--no-sandbox', '--disable-gpu',
  '--hide-scrollbars', 'about:blank'], { stdio: ['ignore', 'pipe', 'pipe'] });
let buf = '';
const waitDevtools = new Promise((resolve, reject) => {
  const t = setTimeout(() => reject(new Error('devtools timeout')), 15000);
  chrome.stderr.on('data', d => { buf += d; const m = buf.match(/ws:\/\/\S+/); if (m) { clearTimeout(t); resolve(); } });
});
await waitDevtools;
await new Promise(r => setTimeout(r, 500));

const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = list.find(t => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map();
ws.addEventListener('message', e => {
  const msg = JSON.parse(e.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg.result ?? msg.error); pending.delete(msg.id); }
});
const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });

await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', {
  width: +W, height: +H, deviceScaleFactor: +DPR, mobile: true,
  screenWidth: +W, screenHeight: +H,
});
await send('Page.navigate', { url });
await new Promise(r => setTimeout(r, 2500));
const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
writeFileSync(out, Buffer.from(shot.data, 'base64'));
console.log(`cdp-shot: ${out} (${+W}x${+H} @${DPR}x)`);
ws.close(); chrome.kill('SIGKILL');
process.exit(0);
