const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const readline = require('readline');

const runId = process.env.RUN_ID || 'RUN-MCP-SMOKE';
const outDir = path.resolve('evidence', 'raw', runId, 'mcp');
fs.mkdirSync(outDir, { recursive: true });

const server = path.resolve('node_modules', '@playwright', 'mcp', 'cli.js');
const child = spawn(process.execPath, [
  server,
  '--headless',
  '--browser', 'chrome',
  '--isolated',
  '--viewport-size', '1280x720',
  '--output-dir', path.join(outDir, 'auto')
], {
  cwd: process.cwd(),
  stdio: ['pipe', 'pipe', 'pipe'],
  windowsHide: true
});

let nextId = 1;
const pending = new Map();
const logLines = [];
const rl = readline.createInterface({ input: child.stdout });
rl.on('line', (line) => {
  if (!line.trim()) return;
  let msg;
  try { msg = JSON.parse(line); } catch { logLines.push(`[non-json] ${line}`); return; }
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) reject(new Error(JSON.stringify(msg.error)));
    else resolve(msg.result);
  } else if (msg.method) {
    logLines.push(`[notification] ${msg.method}`);
  }
});
child.stderr.on('data', (d) => logLines.push(`[stderr] ${d.toString().trim()}`));

function send(method, params, timeoutMs = 60000) {
  const id = nextId++;
  const msg = { jsonrpc: '2.0', id, method, params };
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`timeout: ${method}`));
    }, timeoutMs);
    pending.set(id, {
      resolve: (v) => { clearTimeout(timer); resolve(v); },
      reject: (e) => { clearTimeout(timer); reject(e); }
    });
    child.stdin.write(JSON.stringify(msg) + '\n');
  });
}

function notify(method, params) {
  child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method, params }) + '\n');
}

(async () => {
  const report = { runId, server, outDir, steps: [] };
  try {
    const init = await send('initialize', {
      protocolVersion: '2025-06-18',
      capabilities: {},
      clientInfo: { name: 'mooctest-mcp-smoke', version: '1.0.0' }
    }, 30000);
    report.serverInfo = init.serverInfo;
    report.protocolVersion = init.protocolVersion;
    notify('notifications/initialized', {});
    report.steps.push({ step: 'initialize', ok: true });

    const tools = await send('tools/list', {}, 30000);
    report.toolCount = tools.tools.length;
    report.tools = tools.tools.map((t) => t.name);
    report.steps.push({ step: 'tools/list', ok: true, toolCount: report.toolCount });

    const nav = await send('tools/call', {
      name: 'browser_navigate',
      arguments: { url: 'https://demo.playwright.dev/todomvc' }
    }, 90000);
    report.navigate = nav.content;
    report.steps.push({ step: 'browser_navigate', ok: true });

    const snapshotFile = path.join(outDir, 'mcp-snapshot.yml');
    const snap = await send('tools/call', {
      name: 'browser_snapshot',
      arguments: { filename: path.relative(process.cwd(), snapshotFile).replace(/\\/g, '/') }
    }, 60000);
    report.snapshot = snap.content;
    report.snapshotFile = snapshotFile;
    report.steps.push({ step: 'browser_snapshot', ok: true });

    const shotFile = path.join(outDir, 'mcp-screenshot.png');
    const shot = await send('tools/call', {
      name: 'browser_take_screenshot',
      arguments: {
        filename: path.relative(process.cwd(), shotFile).replace(/\\/g, '/'),
        fullPage: true,
        type: 'png'
      }
    }, 90000);
    report.screenshot = shot.content;
    report.screenshotFile = shotFile;
    report.steps.push({ step: 'browser_take_screenshot', ok: true });

    await send('tools/call', { name: 'browser_close', arguments: {} }, 30000).catch(() => {});
    report.ok = true;
  } catch (err) {
    report.ok = false;
    report.error = err.message;
    report.steps.push({ step: 'error', ok: false, error: err.message });
  } finally {
    try { child.stdin.end(); } catch {}
    setTimeout(() => { try { child.kill(); } catch {} }, 1000);
    report.serverLog = logLines;
    const reportFile = path.join(outDir, 'mcp-smoke.json');
    fs.writeFileSync(reportFile, JSON.stringify(report, null, 2), 'utf8');
    console.log(JSON.stringify({ ok: report.ok, reportFile, toolCount: report.toolCount, error: report.error || null }, null, 2));
    process.exit(report.ok ? 0 : 1);
  }
})();
