(() => {
  const RECORD_PATTERN = /^(?:\d{2}\.){1,4}\d{2}$/;

  function canonicalCode(value) {
    const code = String(value || '').replace(/\D/g, '');
    return code.length >= 2 && code.length <= 10 ? code : null;
  }

  function recordUrl(code) {
    return `/app?record=${encodeURIComponent(code)}`;
  }

  function element(name, className, text) {
    const node = document.createElement(name);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function appendExplorerRecordActions() {
    if (window.location.pathname !== '/app') return;
    document.querySelectorAll('button').forEach((button) => {
      const text = button.textContent.trim();
      const displayedCode = text.match(/\b(?:\d{2}\.){1,4}\d{2}\b/)?.[0];
      const code = canonicalCode(displayedCode);
      if (!code || !/·\s*2026\.08\./.test(text) || button.nextElementSibling?.matches('[data-arancel-record-link]')) return;

      const link = element('a', 'arancel-record-link', 'Inspect verified record');
      link.dataset.arancelRecordLink = 'true';
      link.href = recordUrl(code);
      link.setAttribute('aria-label', `Inspect verified record ${displayedCode}`);
      button.insertAdjacentElement('afterend', link);
    });
  }

  async function fetchJson(path) {
    const response = await fetch(path, { cache: 'no-store' });
    if (!response.ok) throw new Error(`request failed with ${response.status}`);
    return response.json();
  }

  function recordPanelTarget() {
    const input = document.getElementById('app-query');
    return input?.closest('section, main, div') || document.getElementById('root');
  }

  function renderRecordPanel(record, parent, children) {
    const existing = document.querySelector('[data-arancel-record-panel]');
    const panel = existing || element('section', 'arancel-record-panel');
    panel.dataset.arancelRecordPanel = 'true';
    panel.dataset.arancelRecordCode = record.code;
    panel.replaceChildren();

    const heading = element('h2', 'arancel-record-panel__title', `${record.code} · ${record.description}`);
    const meta = element(
      'p',
      'arancel-record-panel__meta',
      `Active verified release ${record.dataset_version} · ${record.level} · ${record.ligie_version}`,
    );
    const fields = element('dl', 'arancel-record-panel__fields');
    [
      ['IGI', record.igi ?? 'Not recorded'],
      ['IGE', record.ige ?? 'Not recorded'],
      ['Unit', record.unit ?? 'Not recorded'],
      ['Validity', record.effective_from || record.effective_to ? `${record.effective_from || '—'} to ${record.effective_to || '—'}` : 'No dated range recorded'],
    ].forEach(([label, value]) => {
      fields.append(element('dt', '', label), element('dd', '', String(value)));
    });

    const links = element('nav', 'arancel-record-panel__links');
    links.setAttribute('aria-label', 'Verified record actions');
    const parentCode = parent?.code ? canonicalCode(parent.code) : null;
    if (parentCode) {
      const parentLink = element('a', '', `Open parent ${parent.code}`);
      parentLink.href = recordUrl(parentCode);
      links.append(parentLink);
    }
    const hierarchy = element('a', '', 'Open verified hierarchy JSON');
    hierarchy.href = `/v1/codes/${encodeURIComponent(record.code)}/parent`;
    hierarchy.target = '_blank';
    hierarchy.rel = 'noreferrer';
    links.append(hierarchy);
    const childrenLink = element('a', '', `${children.length} direct child record${children.length === 1 ? '' : 's'}`);
    childrenLink.href = `/v1/codes/${encodeURIComponent(record.code)}/children`;
    childrenLink.target = '_blank';
    childrenLink.rel = 'noreferrer';
    links.append(childrenLink);
    const sourcesLink = element('a', '', 'Open source evidence');
    sourcesLink.href = `/v1/codes/${encodeURIComponent(record.code)}/provenance`;
    sourcesLink.target = '_blank';
    sourcesLink.rel = 'noreferrer';
    links.append(sourcesLink);

    panel.append(heading, meta, fields, links);
    if (!existing) recordPanelTarget()?.insertAdjacentElement('afterend', panel);
  }

  async function loadRequestedRecord() {
    if (window.location.pathname !== '/app') return;
    const code = canonicalCode(new URLSearchParams(window.location.search).get('record'));
    const rendered = document.querySelector('[data-arancel-record-panel]');
    if (!code || rendered?.dataset.arancelRecordCode === code || document.querySelector('[data-arancel-record-loading]')) return;
    const loading = element('p', 'arancel-record-panel__status', 'Loading verified record…');
    loading.dataset.arancelRecordLoading = 'true';
    recordPanelTarget()?.insertAdjacentElement('afterend', loading);
    try {
      const [record, parent, children] = await Promise.all([
        fetchJson(`/v1/lookup/${encodeURIComponent(code)}`),
        fetchJson(`/v1/codes/${encodeURIComponent(code)}/parent`),
        fetchJson(`/v1/codes/${encodeURIComponent(code)}/children`),
      ]);
      renderRecordPanel(record, parent, children);
    } catch (error) {
      loading.textContent = 'The verified record could not be loaded from the active release.';
      return;
    } finally {
      loading.remove();
    }
  }

  function applyInteractions() {
    appendExplorerRecordActions();
    loadRequestedRecord();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyInteractions, { once: true });
  } else {
    applyInteractions();
  }
  new MutationObserver(applyInteractions).observe(document.documentElement, { childList: true, subtree: true });
})();
