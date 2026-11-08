// GET through curl, used only when Node's own fetch cannot verify a certificate (an antivirus or proxy that re-signs
// HTTPS breaks Node, which ignores the Windows certificate store; curl.exe uses it). The URL is passed on stdin, not as
// an argument, so a token inside it never shows up in the process list.
import { spawnSync } from 'node:child_process';

export function curlGet(url, { curl = 'curl', timeoutMs = 60000 } = {}) {
  const run = spawnSync(curl, ['--silent', '--show-error', '--location', '--max-time', String(Math.ceil(timeoutMs / 1000)), '--write-out', '\n%{http_code}', '--config', '-'], {
    input: `url = "${url.replace(/"/g, '%22')}"\n`,
    encoding: 'utf8',
    maxBuffer: 64 * 1024 * 1024,
  });
  if (run.error || run.status !== 0) return { ok: false, status: 0, text: '', error: run.error?.code || `curl exited with ${run.status}` };
  const split = run.stdout.lastIndexOf('\n');
  const status = Number(run.stdout.slice(split + 1));
  return { ok: status >= 200 && status < 300, status, text: run.stdout.slice(0, split) };
}
