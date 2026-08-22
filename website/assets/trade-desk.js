// Style: estimador evidence-first; el resultado breve y la fuente son primarios, el expediente se revela bajo demanda.
import {
  buildPedimentoChecklist,
  calculateCustomsValue,
  calculateImportEstimate,
  evaluateRrnaOrientation,
  evaluateTmecOrientation,
  TRADE_SOURCES,
} from './trade-tools.js';

const money = new Intl.NumberFormat('es-MX', {
  style: 'currency',
  currency: 'MXN',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const DRAFT_STORAGE_KEY = 'arancel-mx-trade-draft';
const LOCAL_FORM_FIELD_IDS = Object.freeze([
  'tariff-code', 'incoterm', 'product-value', 'freight-value', 'insurance-value',
  'incrementables-value', 'customs-value', 'igi-rate', 'dta-rate', 'iva-rate', 'ieps-rate',
  'tmec-code', 'tmec-origin', 'tmec-vcr', 'tmec-vcr-required', 'tmec-suppliers', 'tmec-bom',
  'tmec-reference-url', 'tmec-reference-consulted-at', 'tmec-reference-note',
  'tmec-rule-reference', 'tmec-vcr-method', 'tmec-certification-reference',
  'tmec-supplier-reference', 'tmec-bom-reference',
  'pedimento-code', 'pedimento-regime', 'pedimento-origin', 'pedimento-value',
  'pedimento-invoice', 'pedimento-transport', 'pedimento-origin-evidence', 'pedimento-rrna-review',
  'rrna-reference-url', 'rrna-reference-consulted-at', 'rrna-reference-note',
]);

const byId = (id) => document.getElementById(id);
const value = (id) => byId(id)?.value ?? '';
const checked = (id) => byId(id)?.checked === true;
let selectedRecord = Object.freeze({ code: null, datasetVersion: null });
let isDraftDirty = false;

function numberValue(id) {
  const raw = value(id).trim();
  return raw === '' ? 0 : Number(raw);
}

function normalizeTariffCode(value) {
  const code = String(value || '').replace(/[.\s-]/g, '');
  return /^\d{8}(?:\d{2})?$/.test(code) ? code : null;
}

function applyTariffRecord(record, { dirty = false } = {}) {
  const code = normalizeTariffCode(record?.code);
  if (!code) return false;
  const rate = Number(record?.igi?.value ?? record?.igi_value);
  byId('tariff-code').value = code;
  byId('tmec-code').value = code;
  byId('pedimento-code').value = code;
  if (Number.isFinite(rate) && rate >= 0) byId('igi-rate').value = String(rate);
  selectedRecord = Object.freeze({
    code,
    datasetVersion: typeof record?.dataset_version === 'string' ? record.dataset_version : null,
  });
  const context = byId('trade-context');
  if (context) {
    context.hidden = false;
    const rateText = typeof record?.igi?.text === 'string' ? record.igi.text : Number.isFinite(rate) ? `${rate}%` : 'sin tasa numérica';
    context.textContent = `Hipótesis cargada: ${code} · IGI publicado ${rateText}${selectedRecord.datasetVersion ? ` · release ${selectedRecord.datasetVersion}` : ''}. Verifica vigencia, clasificación y evidencia.`;
  }
  renderTmecResult();
  renderPedimentoChecklist();
  if (dirty) markDraftDirty();
  return true;
}

function updateStatus(message) {
  const status = byId('trade-status');
  if (status) status.textContent = message;
}

function updateDraftStatus(message) {
  const status = byId('trade-draft-status');
  if (status) status.textContent = message;
}

function markDraftDirty() {
  if (isDraftDirty) return;
  isDraftDirty = true;
  updateDraftStatus('Cambios sin guardar en este navegador.');
}

function setSearchFeedback(message, busy = false) {
  const output = byId('classification-results');
  if (!output) return;
  output.setAttribute('aria-busy', String(busy));
  renderTextMessage(output, message);
}

function renderTextMessage(container, message) {
  if (!container) return;
  const paragraph = document.createElement('p');
  paragraph.className = 'trade-empty';
  paragraph.textContent = message;
  container.replaceChildren(paragraph);
}

function sourceLink(source, testId) {
  return `<a ${testId ? `data-testid="${testId}"` : ''} class="trade-source" href="${source.url}" target="_blank" rel="noreferrer">${source.title}</a>`;
}

function appendSourceLink(container, source, testId) {
  if (!source || typeof source.url !== 'string' || typeof source.title !== 'string') return;
  const link = document.createElement('a');
  link.className = 'trade-source';
  link.href = source.url;
  link.target = '_blank';
  link.rel = 'noreferrer';
  if (testId) link.dataset.testid = testId;
  link.textContent = source.title;
  container.append(link);
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

function buildScenario() {
  const customsValue = calculateCustomsValue({
    directValueMxn: value('customs-value'),
    incoterm: value('incoterm'),
    productValueMxn: numberValue('product-value'),
    freightMxn: numberValue('freight-value'),
    insuranceMxn: numberValue('insurance-value'),
    incrementablesMxn: numberValue('incrementables-value'),
  });
  const estimate = calculateImportEstimate({
    customsValueMxn: customsValue.customsValueMxn,
    igiRatePercent: numberValue('igi-rate'),
    dtaRatePercent: numberValue('dta-rate'),
    iepsRatePercent: numberValue('ieps-rate'),
    ivaRatePercent: numberValue('iva-rate'),
  });
  return Object.freeze({ customsValue, estimate });
}

function calculateEstimate() {
  try {
    const { customsValue, estimate } = buildScenario();
    renderEstimate(estimate, customsValue);
    updateStatus('Escenario orientativo actualizado. Revisa la fuente y la evidencia antes de tomar una decisión.');
  } catch (error) {
    const message = error instanceof Error ? error.message : 'No fue posible calcular el escenario orientativo.';
    renderTextMessage(byId('import-result'), message);
    updateStatus(message);
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
    tmecReferenceUrl: value('tmec-reference-url'),
    tmecReferenceConsultedAt: value('tmec-reference-consulted-at'),
    tmecReferenceNote: value('tmec-reference-note'),
    ruleReference: value('tmec-rule-reference'),
    vcrMethod: value('tmec-vcr-method'),
    certificationReference: value('tmec-certification-reference'),
    supplierDeclarationReference: value('tmec-supplier-reference'),
    billOfMaterialsReference: value('tmec-bom-reference'),
  });
  const container = byId('tmec-result');
  if (!container) return;
  const statusLabel = {
    evidence_required: 'Evidencia requerida',
    threshold_not_met: 'Umbral declarado no alcanzado',
    evidence_review_required: 'Revisión documental requerida',
  }[result.status] || 'Revisión documental requerida';
  const heading = document.createElement('strong');
  heading.textContent = statusLabel;
  const nextStep = document.createElement('p');
  nextStep.textContent = result.nextStep;
  container.replaceChildren(heading, nextStep);
  if (result.status !== 'evidence_required') {
    const vcrTrace = document.createElement('p');
    vcrTrace.className = 'trade-result__caption';
    vcrTrace.textContent = `VCR declarado: ${result.regionalValueContent}% · umbral declarado: ${result.requiredRegionalValueContent}%`;
    container.append(vcrTrace);
  }
  const declaredEvidence = Object.values(result.evidence || {}).filter(Boolean);
  if (declaredEvidence.length) {
    const evidenceTrace = document.createElement('p');
    evidenceTrace.className = 'trade-result__caption';
    evidenceTrace.textContent = `Evidencia declarada: ${declaredEvidence.join(' · ')}`;
    container.append(evidenceTrace);
  }
  const sourceContainer = document.createElement('div');
  sourceContainer.style.marginTop = '10px';
  const sources = Array.isArray(result.source) ? result.source : [result.source];
  const testIds = ['tmec-source', 'tmec-origin-rules-source', 'tmec-origin-procedures-source'];
  sources.forEach((source, index) => appendSourceLink(sourceContainer, source, testIds[index]));
  container.append(sourceContainer);
  const disclaimer = document.createElement('p');
  disclaimer.className = 'trade-disclaimer';
  disclaimer.textContent = result.disclaimer;
  container.append(disclaimer);
}

function renderRrnaMatrix() {
  const container = byId('rrna-matrix');
  if (!container) return;
  const result = evaluateRrnaOrientation({
    tariffCode: value('pedimento-code'),
    hasRrnaReview: checked('pedimento-rrna-review'),
    rrnaReferenceUrl: value('rrna-reference-url'),
    rrnaReferenceConsultedAt: value('rrna-reference-consulted-at'),
    rrnaReferenceNote: value('rrna-reference-note'),
  });
  const heading = document.createElement('strong');
  heading.textContent = result.status === 'evidence_review_required'
    ? 'Evidencia declarada para revisión documental'
    : 'Evidencia pendiente';
  const list = document.createElement('ul');
  list.className = 'trade-checklist';
  result.matrix.forEach((row) => {
    const item = document.createElement('li');
    if (row.complete) item.classList.add('is-complete');
    item.textContent = `${row.label}: ${row.value}`;
    list.append(item);
  });
  const nextStep = document.createElement('p');
  nextStep.className = 'trade-result__caption';
  nextStep.textContent = result.nextStep;
  const disclaimer = document.createElement('p');
  disclaimer.className = 'trade-disclaimer';
  disclaimer.textContent = result.disclaimer;
  container.replaceChildren(heading, list, nextStep, disclaimer);
  appendSourceLink(container, result.source, 'rrna-matrix-source');
}

function renderPedimentoChecklist() {
  renderRrnaMatrix();
  const checklist = buildPedimentoChecklist({
    tariffCode: value('pedimento-code'),
    regime: value('pedimento-regime'),
    originCountry: value('pedimento-origin'),
    customsValueMxn: numberValue('pedimento-value'),
    hasInvoice: checked('pedimento-invoice'),
    hasTransportEvidence: checked('pedimento-transport'),
    hasOriginEvidence: checked('pedimento-origin-evidence'),
    hasRrnaReview: checked('pedimento-rrna-review'),
    rrnaReferenceUrl: value('rrna-reference-url'),
    rrnaReferenceConsultedAt: value('rrna-reference-consulted-at'),
    rrnaReferenceNote: value('rrna-reference-note'),
  });
  const container = byId('pedimento-checklist');
  if (!container) return;
  const state = checklist.status === 'incomplete'
    ? 'Pendientes de revisión documental'
    : 'Revisión documental final requerida';
  const missing = checklist.missing.length
    ? `<p class="trade-result__caption">${state}: ${checklist.missing.join(' · ')}</p>`
    : `<p class="trade-result__caption">${state}: confirma la fuente y la evidencia antes de cualquier operación.</p>`;
  container.innerHTML = `
    ${missing}
    <ul class="trade-checklist">${checklist.checklist
      .map((item) => `<li class="${item.complete ? 'is-complete' : ''}">${item.label}</li>`)
      .join('')}</ul>
    <p class="trade-disclaimer">${checklist.disclaimer}</p>
  `;
}

function revealClassificationResults() {
  const tools = byId('trade-secondary-tools');
  if (tools) tools.open = true;
  const tab = byId('classification-tab');
  if (tab) activateTab(tab);
}

async function searchTariff() {
  const query = value('classification-query').trim();
  const output = byId('classification-results');
  const searchButton = byId('search-tariff');
  if (!query) {
    setSearchFeedback('Describe el producto o ingresa una fracción propuesta para buscar en la release verificada.');
    return;
  }
  if (!output || !searchButton) return;
  revealClassificationResults();
  searchButton.disabled = true;
  searchButton.textContent = 'Buscando…';
  setSearchFeedback(`Consultando la release verificada para “${query}”…`, true);
  try {
    const response = await fetch(`/v1/search?q=${encodeURIComponent(query)}&limit=5`);
    if (!response.ok) throw new Error('La búsqueda verificada no está disponible en este momento.');
    const results = await response.json();
    if (!Array.isArray(results)) {
      throw new Error('La respuesta de la búsqueda verificada no tiene el formato esperado.');
    }
    const records = results
      .map((entry) => entry?.record)
      .filter((record) => record && typeof record.code === 'string' && typeof record.description === 'string');
    if (!records.length) {
      setSearchFeedback('No se encontraron coincidencias. Amplía la descripción técnica y conserva la evidencia del producto.');
      return;
    }
    output.replaceChildren();
    records.forEach((record) => {
      const match = document.createElement('article');
      match.className = 'trade-match';
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.code = record.code;
      if (Number.isFinite(Number(record.igi?.value))) button.dataset.igi = String(record.igi.value);
      button.textContent = `${record.code} · ${record.description}`;
      button.addEventListener('click', () => {
        if (!applyTariffRecord(record, { dirty: true })) return;
        updateStatus(`Se cargó ${button.dataset.code} como hipótesis de trabajo. Verifica clasificación, vigencia y evidencia antes de usarla.`);
      });
      const detail = document.createElement('p');
      const igiText = typeof record.igi?.text === 'string' ? record.igi.text : 'sin tasa numérica';
      const igeText = typeof record.ige?.text === 'string'
        ? record.ige.text
        : typeof record.ige === 'string' ? record.ige : 'sin tasa numérica';
      const datasetVersion = typeof record.dataset_version === 'string' ? record.dataset_version : 'sin versión declarada';
      detail.textContent = `IGI publicado: ${igiText} · IGE publicado: ${igeText} · release ${datasetVersion}`;
      const validity = document.createElement('p');
      const effectiveFrom = typeof record.effective_from === 'string' ? record.effective_from : 'sin fecha publicada';
      const currentStatus = record.is_current === true ? 'vigente' : record.is_current === false ? 'no vigente' : 'vigencia sin confirmar';
      const ligieVersion = typeof record.ligie_version === 'string' ? ` · LIGIE ${record.ligie_version}` : '';
      const validityBasis = typeof record.validity_basis === 'string' ? ` · ${record.validity_basis}` : '';
      validity.textContent = `Vigencia de release: ${effectiveFrom} · ${currentStatus}${ligieVersion}${validityBasis}`;
      const provenance = document.createElement('a');
      provenance.className = 'trade-source';
      provenance.href = `/v1/codes/${encodeURIComponent(record.code)}/provenance`;
      provenance.textContent = 'Ver procedencia registrada';
      match.append(button, detail, validity, provenance);
      output.append(match);
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'La búsqueda verificada no está disponible en este momento.';
    setSearchFeedback(message);
  } finally {
    output.setAttribute('aria-busy', 'false');
    searchButton.disabled = false;
    searchButton.textContent = 'Buscar';
  }
}

async function preloadTariffFromQuery() {
  const code = normalizeTariffCode(new URLSearchParams(window.location.search).get('code'));
  if (!code) return;
  const context = byId('trade-context');
  if (context) {
    context.hidden = false;
    context.textContent = `Consultando ${code} en la release verificada…`;
  }
  try {
    const response = await fetch(`/v1/ficha/${encodeURIComponent(code)}`);
    if (!response.ok) throw new Error('El registro verificado no está disponible.');
    const payload = await response.json();
    if (!applyTariffRecord(payload?.record || payload)) throw new Error('El registro verificado no contiene una fracción utilizable.');
    updateStatus(`Se cargó ${code} desde la ficha verificada. Revisa vigencia y evidencia antes de calcular.`);
  } catch {
    byId('tariff-code').value = code;
    if (context) context.textContent = `La fracción ${code} se conservó como hipótesis, pero su tasa verificada no pudo cargarse. Consulta la release antes de calcular.`;
    updateStatus('No fue posible cargar la tasa verificada desde la ficha.');
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
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => activateTab(tab));
    tab.addEventListener('keydown', (event) => {
      const lastIndex = tabs.length - 1;
      const targetIndex = {
        ArrowRight: index === lastIndex ? 0 : index + 1,
        ArrowLeft: index === 0 ? lastIndex : index - 1,
        Home: 0,
        End: lastIndex,
      }[event.key];
      if (targetIndex === undefined) return;
      event.preventDefault();
      const target = tabs[targetIndex];
      target.focus();
      activateTab(target);
    });
  });
}

function buildLocalTraceability() {
  const { customsValue, estimate } = buildScenario();
  const currentTariffCode = value('tariff-code').trim() || null;
  const selectedDataset = selectedRecord.code === currentTariffCode ? selectedRecord : { code: null, datasetVersion: null };
  return Object.freeze({
    schema_version: 1,
    saved_at: new Date().toISOString(),
    scenario_status: estimate.status,
    dataset: Object.freeze({
      version: selectedDataset.datasetVersion,
      record_code: currentTariffCode,
    }),
    rates_percent: Object.freeze({
      igi: numberValue('igi-rate'),
      dta: numberValue('dta-rate'),
      iva: numberValue('iva-rate'),
      ieps: numberValue('ieps-rate'),
    }),
    customs_value_method: customsValue.method,
    inputs: Object.freeze({
      incoterm: value('incoterm'),
      direct_customs_value_mxn: value('customs-value'),
      product_value_mxn: value('product-value'),
      freight_mxn: value('freight-value'),
      insurance_mxn: value('insurance-value'),
      incrementables_mxn: value('incrementables-value'),
    }),
    calculation: Object.freeze({
      items: estimate.items,
      total_contributions: estimate.totalContributions,
      landed_cost: estimate.landedCost,
    }),
    sources: Object.freeze([TRADE_SOURCES.costs, TRADE_SOURCES.classification]),
    review_references: Object.freeze({
      tmec: Object.freeze({
        url: value('tmec-reference-url'),
        consulted_at: value('tmec-reference-consulted-at'),
        note: value('tmec-reference-note'),
        rule_reference: value('tmec-rule-reference'),
        vcr_method: value('tmec-vcr-method'),
        certification_reference: value('tmec-certification-reference'),
        supplier_reference: value('tmec-supplier-reference'),
        bill_of_materials_reference: value('tmec-bom-reference'),
      }),
      rrna: Object.freeze({
        url: value('rrna-reference-url'),
        consulted_at: value('rrna-reference-consulted-at'),
        note: value('rrna-reference-note'),
      }),
    }),
    assumptions: Object.freeze([
      'Los valores y tasas fueron declarados por la persona usuaria.',
      'El snapshot es local y orientativo; no determina contribuciones, origen, clasificación ni cumplimiento.',
    ]),
  });
}

function captureLocalFormState() {
  return Object.freeze(Object.fromEntries(LOCAL_FORM_FIELD_IDS.map((id) => {
    const field = byId(id);
    return [id, field?.type === 'checkbox' ? field.checked : field?.value ?? ''];
  })));
}

function restoreLocalFormState(form) {
  if (!form || typeof form !== 'object') return;
  LOCAL_FORM_FIELD_IDS.forEach((id) => {
    const field = byId(id);
    if (!field || !(id in form)) return;
    if (field.type === 'checkbox') field.checked = form[id] === true;
    else field.value = typeof form[id] === 'string' ? form[id] : '';
  });
}

function persistDraft() {
  const draft = {
    saved_at: new Date().toISOString(),
    tariff_code: value('tariff-code'),
    customs_value_mxn: value('customs-value'),
    product_value_mxn: value('product-value'),
    origin_country: value('tmec-origin'),
    form: captureLocalFormState(),
    traceability: null,
  };
  try {
    draft.traceability = buildLocalTraceability();
  } catch {
    // Incomplete inputs remain a legitimate local working draft; only the calculation snapshot is unavailable.
  }
  try {
    localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
  } catch {
    const message = 'No se pudo guardar el expediente local por un problema de almacenamiento. Conserva el formulario abierto o libera espacio en este navegador.';
    updateDraftStatus(message);
    updateStatus(message);
    return;
  }
  isDraftDirty = false;
  const message = draft.traceability
    ? 'Expediente guardado localmente con trazabilidad orientativa.'
    : 'Expediente local incompleto guardado; completa los valores para generar un snapshot orientativo.';
  updateDraftStatus(message);
  updateStatus(message);
}

function clearDraft() {
  try {
    localStorage.removeItem(DRAFT_STORAGE_KEY);
  } catch {
    const message = 'No se pudo borrar el expediente local por un problema de almacenamiento.';
    updateDraftStatus(message);
    updateStatus(message);
    return;
  }
  isDraftDirty = false;
  const message = 'Expediente local eliminado de este navegador. Los valores visibles permanecen abiertos hasta que cierres o recargues la mesa.';
  updateDraftStatus(message);
  updateStatus(message);
}

function restoreDraft() {
  try {
    const draft = JSON.parse(localStorage.getItem(DRAFT_STORAGE_KEY) || 'null');
    if (!draft || typeof draft !== 'object') return;
    if (draft.form) {
      restoreLocalFormState(draft.form);
    } else {
      if (draft.tariff_code) byId('tariff-code').value = draft.tariff_code;
      if (draft.customs_value_mxn) byId('customs-value').value = draft.customs_value_mxn;
      if (draft.product_value_mxn) byId('product-value').value = draft.product_value_mxn;
      if (draft.origin_country) byId('tmec-origin').value = draft.origin_country;
    }
    const dataset = draft.traceability?.dataset;
    if (dataset && typeof dataset === 'object') {
      selectedRecord = Object.freeze({
        code: typeof dataset.record_code === 'string' ? dataset.record_code : null,
        datasetVersion: typeof dataset.version === 'string' ? dataset.version : null,
      });
    }
    updateDraftStatus('Expediente local restaurado en este navegador.');
  } catch {
    localStorage.removeItem(DRAFT_STORAGE_KEY);
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
  ['tmec-code', 'tmec-origin', 'tmec-vcr', 'tmec-vcr-required', 'tmec-suppliers', 'tmec-bom', 'tmec-reference-url', 'tmec-reference-consulted-at', 'tmec-reference-note', 'tmec-rule-reference', 'tmec-vcr-method', 'tmec-certification-reference', 'tmec-supplier-reference', 'tmec-bom-reference'].forEach((id) => {
    const field = byId(id);
    field.addEventListener('change', renderTmecResult);
    if (field.type !== 'checkbox' && field.tagName !== 'SELECT') field.addEventListener('input', renderTmecResult);
  });
  ['pedimento-code', 'pedimento-regime', 'pedimento-origin', 'pedimento-value', 'pedimento-invoice', 'pedimento-transport', 'pedimento-origin-evidence', 'pedimento-rrna-review', 'rrna-reference-url', 'rrna-reference-consulted-at', 'rrna-reference-note'].forEach((id) => {
    const field = byId(id);
    field.addEventListener('change', renderPedimentoChecklist);
    if (field.type !== 'checkbox' && field.tagName !== 'SELECT') field.addEventListener('input', renderPedimentoChecklist);
  });
  LOCAL_FORM_FIELD_IDS.forEach((id) => {
    const field = byId(id);
    if (!field) return;
    const eventName = field.type === 'checkbox' || field.tagName === 'SELECT' ? 'change' : 'input';
    field.addEventListener(eventName, markDraftDirty);
  });
  byId('tariff-code').addEventListener('input', () => {
    if (selectedRecord.code !== value('tariff-code').trim()) {
      selectedRecord = Object.freeze({ code: null, datasetVersion: null });
    }
  });
  byId('save-draft')?.addEventListener('click', persistDraft);
  byId('clear-draft')?.addEventListener('click', clearDraft);
  byId('rrna-source').href = TRADE_SOURCES.rrna.url;
  byId('rrna-source').textContent = TRADE_SOURCES.rrna.title;
  byId('costs-source').href = TRADE_SOURCES.costs.url;
  byId('costs-source').textContent = TRADE_SOURCES.costs.title;
  void preloadTariffFromQuery();
}

initialize();
