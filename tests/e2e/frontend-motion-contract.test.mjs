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

test('functional controls use the shared motion tokens, without bounce, and menus also animate out', async () => {
  const css = await read('frontend/src/styles.css');
  // Shared tokens: short press feedback, ~200 ms menus, an exit about 20 % shorter than the entrance.
  assert.match(css, /--motion-fast:120ms;[^}]*--motion-ui:200ms;[^}]*--motion-exit:160ms;[^}]*--motion-standard:240ms;[^}]*--motion-slow:360ms;/);
  // Popovers start at 0.95 and the press scale is 0.97, on the calm ease-out curve rather than the spring.
  assert.match(css, /@keyframes pop-in \{ from \{ opacity:0; transform:translateY\(-\.25rem\) scale\(\.95\)/);
  assert.match(css, /\.button:active:not\(:disabled\),\.chip:active,\.search-trigger:active \{ transform:scale\(\.97\)/);
  assert.doesNotMatch(css, /\.button,\.chip,\.search-trigger \{[^}]*var\(--spring\)/);
  // The success pulse is subtle.
  assert.match(css, /@keyframes pop \{[^@]*?45% \{ transform:scale\(1\.035\)/);
  // The dropdown leaves from its trigger, faster than it enters, and a closed panel is removed from focus and clicks.
  assert.match(css, /\.nav-menu__panel:not\(\[data-open='true'\]\) \{ display:none; \}/);
  assert.match(css, /\.nav-menu__panel \{ transform-origin:top left;[^}]*display var\(--motion-ui\) allow-discrete/);
  assert.match(css, /\.nav-menu__panel:not\(\[data-open='true'\]\) \{ opacity:0;[^}]*transition-duration:var\(--motion-exit\)/);
  const app = await read('frontend/src/App.jsx');
  assert.match(app, /className="nav-menu__panel" data-open=\{open\}/);
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
