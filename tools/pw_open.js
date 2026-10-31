const { spawn, execFileSync } = require('child_process');

const sleep = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);

const session = process.argv[2] || 'mooctest';
const url = process.argv[3] || 'about:blank';
const browser = process.argv[4] || 'chrome';
const timeoutMs = Number(process.argv[5] || 30000);

function list() {
  return execFileSync('cmd.exe', ['/c', 'npx', '--no-install', 'playwright-cli', 'list'], {
    encoding: 'utf8', timeout: 15000, windowsHide: true
  });
}

const child = spawn('cmd.exe', [
  '/c', 'npx', '--no-install', 'playwright-cli',
  `-s=${session}`, 'open', url, `--browser=${browser}`
], {
  detached: true,
  stdio: 'ignore',
  windowsHide: true
});
child.unref();

const deadline = Date.now() + timeoutMs;
while (Date.now() < deadline) {
  try {
    const out = list();
    if (out.includes(session)) {
      console.log(`OPENED ${session}`);
      process.exit(0);
    }
  } catch (err) {
    // CLI may be briefly unavailable while the daemon starts.
  }
  sleep(500);
}
console.error(`Timed out waiting for Playwright session ${session}`);
process.exit(1);
