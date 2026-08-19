import {
  buildPedimentoChecklist,
  calculateCustomsValue,
  calculateImportEstimate,
  evaluateTmecOrientation,
  TRADE_SOURCES,
} from './trade-tools.js';

const money = new Intl.NumberFormat('es-MX', {
  style: 'currency',
  currency: 'MXN',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const byId = (id) => document.getElementById(id);
const value = (id) => byId(id)?.value ?? '';
const checked = (id) => byId(id)?.checked === true;

function numberValue(id) {
  const raw = value(id).trim();
  return raw === '' ? 0 : Number(raw);
}

function updateStatus(message) {
  const status = byId('trade-status');
  if (status) status.textContent = message;
}

function sourceLink(source, testId) {
  return `<a ${testId ? `data-testid="${testId}"` : ''} class="trade-source" href="${source.url}" target="_blank" rel="noreferrer">${source.title}</a>`;
}

function renderEstimate(estimate, customsValue) {
  const result = byId('import-result');
  if (!result) return;
  const rows = estimate.items
    .map(
      (item) => `<div class="trade-breakdown__row"><span>${item.label}</span><strong>${money.format(item.amount)}</strong></div>`,
    )
    .join('');
  result.innerHTML = `
    <p class="trade-result__eyebrow">Escenario de contribuciones</p>
    <p class="trade-result__amount">${money.format(estimate.totalContributions)}</p>
    <p class="trade-result__caption">Contribuciones estimadas; costo orientativo total: <strong>${money.format(estimate.landedCost)}</strong></p>
    <p class="trade-result__caption">Base ${customsValue.method === 'direct_value' ? 'directa declarada' : `por componentes ${customsValue.incoterm}`}: <strong>${money.format(customsValue.customsValueMxn)}</strong></p>
    <div class="trade-breakdown">${rows}</div>
    <p class="trade-disclaimer">${estimate.disclaimer}</p>
  `;
}

function calculateEstimate() {
  try {
    const directValue = value('customs-value').trim();
    const componentValue = calculateCustomsValue({
      incoterm: value('incoterm'),
      productValueMxn: numberValue('product-value'),
      freightMxn: numberValue('freight-value'),
      insuranceMxn: numberValue('insurance-value'),
      incrementablesMxn: numberValue('incrementables-value'),
    });
    const customsValue = directValue
      ? { method: 'direct_value', customsValueMxn: Number(directValue) }
      : componentValue;
    const estimate = calculateImportEstimate({
      customsValueMxn: customsValue.customsValueMxn,
      igiRatePercent: numberValue('igi-rate'),
      dtaRatePercent: numberValue('dta-rate'),
      iepsRatePercent: numberValue('ieps-rate'),
      ivaRatePercent: numberValue('iva-rate'),
    });
    renderEstimate(estimate, customsValue);
    updateStatus('Escenario orientativo actualizado. Revisa la fuente y la evidencia antes de tomar una decisión.');
  } catch (error) {
    byId('import-result').innerHTML = `<p class="trade-empty">${error.message}</p>`;
    updateStatus(error.message);
  }
}

function renderTmecResult() {
  const result = evaluateTmecOrientation({
    tariffCode: value('tmec-code'),
    originCountry: value('tmec-origin'),
    regionalValueContent: numberValue('tmec-vcr'),
    requiredRegionalValueContent: numberValue('tmec-vcr-required'),
    supplierDeclarations: checked('tmec-suppliers'),
    billOfMaterials: checked('tmec-bom'),
  });
  const container = byId('tmec-result');
  if (!container) return;
  container.innerHTML = `
    <strong>${result.status === 'evidence_review_required' ? 'Revisión documental requerida' : 'Evidencia requerida'}</strong>
    ${result.nextStep}
    <div style="margin-top:10px">${sourceLink(result.source, 'tmec-source')}</div>
    <p class="trade-disclaimer">${result.disclaimer}</p>
  `;
}

function renderPedimentoChecklist() {
  const checklist = buildPedimentoChecklist({
    tariffCode: value('pedimento-code'),
    regime: value('pedimento-regime'),
    originCountry: value('pedimento-origin'),
    customsValueMxn: numberValue('pedimento-value'),
    hasInvoice: checked('pedimento-invoice'),
    hasTransportEvidence: checked('pedimento-transport'),
    hasOriginEvidence: checked('pedimento-origin-evidence'),
  });
  const container = byId('pedimento-checklist');
  if (!container) return;
  container.innerHTML = `
    <ul class="trade-checklist">${checklist.checklist
      .map((item) => `<li class="${item.complete ? 'is-complete' : ''}">${item.label}</li>`)
      .join('')}</ul>
    <p class="trade-disclaimer">${checklist.disclaimer}</p>
  `;
}

async function searchTariff() {
  const query = value('classification-query').trim();
  const output = byId('classification-results');
  if (!query) {
    output.innerHTML = '<p class="trade-empty">Describe el producto o ingresa una fracción propuesta para buscar en la release verificada.</p>';
    return;
  }
  output.innerHTML = '<p class="trade-empty">Consultando la release verificada…</p>';
  try {
    const response = await fetch(`/v1/search?q=${encodeURIComponent(query)}&limit=5`);
    if (!response.ok) throw new Error('La búsqueda verificada no está disponible en este momento.');
    const results = await response.json();
    if (!results.length) {
      output.innerHTML = '<p class="trade-empty">No se encontraron coincidencias. Amplía la descripción técnica y conserva la evidencia del producto.</p>';
      return;
    }
    output.innerHTML = results
      .map(({ record }) => `
        <article class="trade-match">
          <button type="button" data-code="${record.code}" data-igi="${record.igi?.value ?? ''}">${record.code} · ${record.description}</button>
          <p>IGI publicado: ${record.igi?.text ?? 'sin tasa numérica'} · release ${record.dataset_version}</p>
        </article>
      `)
      .join('');
    output.querySelectorAll('button[data-code]').forEach((button) => {
      button.addEventListener('click', () => {
        byId('tariff-code').value = button.dataset.code;
        byId('tmec-code').value = button.dataset.code;
        byId('pedimento-code').value = button.dataset.code;
        if (button.dataset.igi) byId('igi-rate').value = button.dataset.igi;
        updateStatus(`Se cargó ${button.dataset.code} como hipótesis de trabajo. Verifica clasificación, vigencia y evidencia antes de usarla.`);
      });
    });
  } catch (error) {
    output.innerHTML = `<p class="trade-empty">${error.message}</p>`;
  }
}

function activateTab(tab) {
  document.querySelectorAll('[role="tab"]').forEach((button) => {
    const selected = button === tab;
    button.setAttribute('aria-selected', String(selected));
    byId(button.getAttribute('aria-controls')).hidden = !selected;
  });
}

function bindTabs() {
  document.querySelectorAll('[role="tab"]').forEach((tab) => {
    tab.addEventListener('click', () => activateTab(tab));
  });
}

function persistDraft() {
  const draft = {
    saved_at: new Date().toISOString(),
    tariff_code: value('tariff-code'),
    customs_value_mxn: value('customs-value'),
    product_value_mxn: value('product-value'),
    origin_country: value('tmec-origin'),
  };
  localStorage.setItem('arancel-mx-trade-draft', JSON.stringify(draft));
  updateStatus('Expediente de trabajo guardado únicamente en este navegador.');
}

function restoreDraft() {
  try {
    const draft = JSON.parse(localStorage.getItem('arancel-mx-trade-draft') || 'null');
    if (!draft) return;
    if (draft.tariff_code) byId('tariff-code').value = draft.tariff_code;
    if (draft.customs_value_mxn) byId('customs-value').value = draft.customs_value_mxn;
    if (draft.product_value_mxn) byId('product-value').value = draft.product_value_mxn;
    if (draft.origin_country) byId('tmec-origin').value = draft.origin_country;
  } catch {
    localStorage.removeItem('arancel-mx-trade-draft');
  }
}

function initialize() {
  bindTabs();
  restoreDraft();
  renderTmecResult();
  renderPedimentoChecklist();
  byId('calculate-import').addEventListener('click', calculateEstimate);
  byId('search-tariff').addEventListener('click', searchTariff);
  byId('classification-query').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      searchTariff();
    }
  });
  ['tmec-code', 'tmec-origin', 'tmec-vcr', 'tmec-vcr-required', 'tmec-suppliers', 'tmec-bom'].forEach((id) => {
    byId(id).addEventListener('change', renderTmecResult);
  });
  ['pedimento-code', 'pedimento-regime', 'pedimento-origin', 'pedimento-value', 'pedimento-invoice', 'pedimento-transport', 'pedimento-origin-evidence'].forEach((id) => {
    byId(id).addEventListener('change', renderPedimentoChecklist);
  });
  byId('save-draft').addEventListener('click', persistDraft);
  byId('rrna-source').href = TRADE_SOURCES.rrna.url;
  byId('rrna-source').textContent = TRADE_SOURCES.rrna.title;
  byId('costs-source').href = TRADE_SOURCES.costs.url;
  byId('costs-source').textContent = TRADE_SOURCES.costs.title;
  calculateEstimate();
}

initialize();
