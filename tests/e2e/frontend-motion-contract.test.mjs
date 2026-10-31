import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');
const read = (file) => readFile(path.join(root, file), 'utf8');

test('motion is defined as a spring easing and only runs when motion is allowed', async () => {
  const css = await read('frontend/src/styles.css');
  assert.match(css, /--spring:linear\(0,/);
  const motion = css.slice(css.indexOf('@keyframes pop-in'));
  // Every entrance animation sits inside the no-preference query, and the view-transition pseudo-elements are switched off for reduced motion.
  assert.match(motion, /@media \(prefers-reduced-motion:no-preference\) \{[^@]*\.home-tile,/s);
  assert.match(motion, /@media \(prefers-reduced-motion:reduce\) \{ ::view-transition-group\(\*\)/);
});

test('large corners use continuous curvature only where the browser supports it', async () => {
  const css = await read('frontend/src/styles.css');
  assert.match(css, /@supports \(corner-shape:squircle\) \{[^}]*\.home-tile__badge[^}]*corner-shape:squircle/s);
});

test('page transitions and counters honor reduced motion', async () => {
  const countUp = await read('frontend/src/count-up.jsx');
  assert.match(countUp, /prefers-reduced-motion: reduce/);
  assert.match(countUp, /className="sr-only"/);
  const app = await read('frontend/src/App.jsx');
  assert.match(app, /viewTransition/);
});
