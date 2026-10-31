const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const readline = require('readline');

const runId = process.env.RUN_ID || 'RUN-TOOLCHECK-01';
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
], { cwd: process.cwd(), stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true });

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
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`timeout: ${method}`));
    }, timeoutMs);
    pending.set(id, {
      resolve: (v) => { clearTimeout(timer); resolve(v); },
      reject: (e) => { clearTimeout(timer); reject(e); }
    });
    child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
  });
}
function notify(method, params) {
  child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method, params }) + '\n');
}
function textOf(result) {
  if (!result || !Array.isArray(result.content)) return '';
  return result.content.filter((c) => c.type === 'text').map((c) => c.text).join('\n');
}

(async () => {
  const report = { runId, steps: [], tools: [] };
  const call = async (name, args, timeout = 60000) => {
    const res = await send('tools/call', { name, arguments: args }, timeout);
    const text = textOf(res);
    report.steps.push({ tool: name, ok: true, text: text.slice(0, 1200) });
    return { res, text };
  };
  try {
    const init = await send('initialize', {
      protocolVersion: '2025-06-18', capabilities: {},
      clientInfo: { name: 'mooctest-mcp-toolcheck', version: '1.0.0' }
    }, 30000);
    report.serverInfo = init.serverInfo;
    report.protocolVersion = init.protocolVersion;
    notify('notifications/initialized', {});
    const tools = await send('tools/list', {}, 30000);
    report.tools = tools.tools.map((t) => t.name);
    report.steps.push({ tool: 'tools/list', ok: true, count: report.tools.length });

    await call('browser_navigate', { url: 'https://demo.playwright.dev/todomvc' }, 90000);
    await call('browser_type', { target: 'input.new-todo', text: 'MCP tool check', submit: true });
    await call('browser_wait_for', { text: 'MCP tool check' });
    await call('browser_find', { text: 'MCP tool check' });
    const snap = path.join(outDir, 'mcp-snapshot.yml');
    await call('browser_snapshot', { filename: path.relative(process.cwd(), snap).replace(/\\/g, '/') });
    await call('browser_click', { target: 'input.toggle' });
    const evalResult = await call('browser_evaluate', {
      function: "() => ({items: document.querySelectorAll('.todo-list li').length, checked: document.querySelectorAll('input.toggle:checked').length, count: document.querySelector('.todo-count')?.textContent})"
    });
    report.evaluate = evalResult.text;
    await call('browser_resize', { width: 1024, height: 768 });
    await call('browser_console_messages', { level: 'error' }, 30000);
    await call('browser_network_requests', { static: false }, 30000);
    await call('browser_tabs', { action: 'list' }, 30000);
    const shot = path.join(outDir, 'mcp-fullpage.png');
    await call('browser_take_screenshot', {
      filename: path.relative(process.cwd(), shot).replace(/\\/g, '/'),
      fullPage: true, type: 'png'
    }, 90000);
    report.screenshotFile = shot;
    report.snapshotFile = snap;
    await call('browser_close', {}, 30000);
    report.ok = true;
  } catch (err) {
    report.ok = false;
    report.error = err.message;
    report.steps.push({ tool: 'error', ok: false, error: err.message });
  } finally {
    try { child.stdin.end(); } catch {}
    setTimeout(() => { try { child.kill(); } catch {} }, 1000);
    report.log = logLines;
    const reportFile = path.join(outDir, 'mcp-toolcheck.json');
    fs.writeFileSync(reportFile, JSON.stringify(report, null, 2), 'utf8');
    console.log(JSON.stringify({
      ok: report.ok, reportFile, toolCount: report.tools.length,
      steps: report.steps.map((s) => s.tool), error: report.error || null
    }, null, 2));
    process.exit(report.ok ? 0 : 1);
  }
})();
