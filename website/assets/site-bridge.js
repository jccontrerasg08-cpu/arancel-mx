const consumerQuickstart = 'https://github.com/jccontrerasg08-cpu/arancel-mx/blob/main/docs/consumer-quickstart.md';
const hostedExplorer = 'https://arancel-mx.vercel.app/app';

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
  const root = document.getElementById('root') || document.body;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    if (/release\s*\/\s*data-\d{4}\.\d{2}\.\d{2}/.test(node.nodeValue)) {
      node.nodeValue = node.nodeValue.replace(
        /release\s*\/\s*data-\d{4}\.\d{2}\.\d{2}/,
        `release / ${activeDatasetTag}`,
      );
    }
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
  redirectFormerExplorerLinks();
  updateStandaloneCopy();
  synchronizeDisplayedRelease();
}

applyPublicSiteBridge();
new MutationObserver(applyPublicSiteBridge).observe(document.body, { childList: true, subtree: true });
window.addEventListener('load', synchronizeDisplayedRelease, { once: true });
