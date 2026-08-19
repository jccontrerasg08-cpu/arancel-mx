const consumerQuickstart = 'https://github.com/jccontrerasg08-cpu/arancel-mx/blob/main/docs/consumer-quickstart.md';
const hostedExplorer = 'https://arancel-mx.vercel.app/app';

function repairNavigationDestinations() {
  const routes = new Map([
    ['/moa-guide', '/moa'],
    ['/product', '/app'],
  ]);
  document.querySelectorAll('a[href]').forEach((link) => {
    const destination = routes.get(link.getAttribute('href'));
    if (destination) link.setAttribute('href', destination);
  });
  const destination = routes.get(window.location.pathname);
  if (destination) window.location.replace(`${destination}${window.location.search}${window.location.hash}`);
}

function redirectFormerExplorerLinks() {
  document.querySelectorAll(`a[href="${hostedExplorer}"]`).forEach((link) => {
    link.href = consumerQuickstart;
    link.target = '_blank';
    link.rel = 'noreferrer';
    link.setAttribute('aria-label', 'Open the consumer quickstart on GitHub');
    if (link.textContent.trim() === 'Open explorer') link.textContent = 'Start with the guide';
  });
}

const copyUpdates = new Map([
  ['arancel-mx.vercel.app/app', 'GitHub releases, CLI & guides'],
  ['The hosted explorer retrieves a verified release; this preview preserves its exact navigation order.', 'The public site preserves the documented hierarchy; use a release, CLI, or separately deployed API to query verified data.'],
  ['Use the Python package, CLI, public API, and hosted explorer against a verified version.', 'Use the Python package, CLI, and a separately deployed API against a verified version.'],
  ['read-only API, explorer, release manifests', 'separate read-only API, release manifests'],
  ['Search in explorer', 'Open consumer guide'],
]);

function updateStandaloneCopy() {
  const walker = document.createTreeWalker(document.getElementById('root') || document.body, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    for (const [oldCopy, newCopy] of copyUpdates) {
      if (node.nodeValue.includes(oldCopy)) node.nodeValue = node.nodeValue.replaceAll(oldCopy, newCopy);
    }
  }
}

let activeDatasetTag = null;
let releaseMetadataRequest = null;

function updateDisplayedRelease() {
  if (!activeDatasetTag) return;
  document.querySelectorAll('.release-window code').forEach((label) => {
    if (/^release\s*\/\s*data-\d{4}\.\d{2}\.\d{2}$/.test(label.textContent)) {
      label.textContent = `release / ${activeDatasetTag}`;
    }
  });

  const currentReleasePattern = /(?:data-)?2026\.08\.(?:15|16)/g;
  const root = document.getElementById('root');
  if (!root) return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    if (node.parentElement?.closest('script, style, a[href*="releases/tag"]')) continue;
    if (currentReleasePattern.test(node.nodeValue)) {
      node.nodeValue = node.nodeValue.replace(currentReleasePattern, activeDatasetTag);
    }
    currentReleasePattern.lastIndex = 0;
  }
}

function synchronizeDisplayedRelease() {
  if (activeDatasetTag) {
    updateDisplayedRelease();
    return;
  }
  if (releaseMetadataRequest) return;
  releaseMetadataRequest = fetch('/v1/meta', { cache: 'no-store' })
    .then((response) => (response.ok ? response.json() : null))
    .then((metadata) => {
      if (metadata && typeof metadata.dataset_tag === 'string') {
        activeDatasetTag = metadata.dataset_tag;
        updateDisplayedRelease();
      }
    })
    .catch(() => {
      releaseMetadataRequest = null;
    });
}

function applyPublicSiteBridge() {
  repairNavigationDestinations();
  redirectFormerExplorerLinks();
  updateStandaloneCopy();
  synchronizeDisplayedRelease();
}

applyPublicSiteBridge();
new MutationObserver(applyPublicSiteBridge).observe(document.body, { childList: true, subtree: true });
window.addEventListener('load', () => {
  let attempts = 0;
  const timer = window.setInterval(() => {
    synchronizeDisplayedRelease();
    attempts += 1;
    if (attempts >= 12) window.clearInterval(timer);
  }, 250);
}, { once: true });
