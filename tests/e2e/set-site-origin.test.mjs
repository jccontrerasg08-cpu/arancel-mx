import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { currentOrigin, rewriteOrigin, validateOrigin } from '../../scripts/set-site-origin.mjs';

test('accepts only a bare https origin', () => {
  assert.equal(validateOrigin('https://www.example.com'), 'https://www.example.com');
  for (const bad of ['http://example.com', 'https://example.com/', 'https://example.com/app', 'example.com', 'https://example.com?x=1']) {
    assert.throws(() => validateOrigin(bad), undefined, bad);
  }
});

test('rewrites the full origin and the bare host, and nothing else', () => {
  const text = 'a https://arancel-mx.vercel.app/app b arancel-mx.vercel.app/app c https://jccontrerasg08-cpu.github.io/arancel-mx/v1 d /https:\\/\\/arancel-mx\\.vercel\\.app/';
  assert.equal(
    rewriteOrigin(text, 'https://arancel-mx.vercel.app', 'https://www.example.com'),
    'a https://www.example.com/app b www.example.com/app c https://jccontrerasg08-cpu.github.io/arancel-mx/v1 d /https:\\/\\/www\\.example\\.com/',
  );
});

test('every tracked file that names the site uses the one configured origin', () => {
  const origin = currentOrigin();
  assert.match(origin, /^https:\/\/[^/]+$/);
  const canonical = /<link rel="canonical" href="(https:\/\/[^/"]+)/;
  const pages = ['frontend/index.html', 'src/arancel_mx/api/static/site/index.html', 'src/arancel_mx/api/static/site/trade.html', 'src/arancel_mx/api/static/site/learn.html'];
  for (const file of pages) assert.equal(canonical.exec(readFileSync(file, 'utf8'))?.[1], origin, file);
  assert.match(readFileSync('src/arancel_mx/api/static/site/sitemap.xml', 'utf8'), new RegExp(`<loc>${origin.replace(/[\\^$.*+?()[\]{}|]/g, '\\$&')}/</loc>`));
  assert.ok(readFileSync('src/arancel_mx/api/static/site/robots.txt', 'utf8').includes(`Sitemap: ${origin}/sitemap.xml`));
  assert.ok(readFileSync('scripts/check_public_service.py', 'utf8').includes(`DEFAULT_BASE_URL = "${origin}"`));
});

test('a dry run lists the files and changes none', () => {
  const before = execFileSync('git', ['status', '--porcelain'], { encoding: 'utf8' });
  const output = execFileSync('node', ['scripts/set-site-origin.mjs', 'https://dry-run.invalid', '--dry-run'], { encoding: 'utf8' });
  assert.match(output, /Would change \d+ files/);
  assert.match(output, /frontend\/src\/page-meta\.js/);
  assert.equal(execFileSync('git', ['status', '--porcelain'], { encoding: 'utf8' }), before);
});
