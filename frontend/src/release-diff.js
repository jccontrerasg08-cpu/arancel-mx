const VERSION = /^\d{4}\.\d{2}\.\d{2}$/u;
const CODE = /^(?:\d{2}){1,5}$/u;
const VERIFIED = 'verified_snapshots';

export const RELEASE_DIFF_EVENTS = {
  row_added: ['Alta', 'Added'],
  row_removed: ['Baja', 'Removed'],
  description_changed: ['Descripción', 'Description'],
  igi_changed: ['IGI', 'Import duty'],
  ige_changed: ['IGE', 'Export duty'],
  unit_changed: ['Unidad de medida', 'Unit of measure'],
  hierarchy_changed: ['Jerarquía', 'Hierarchy'],
};

const isValue = (value) => value === null || typeof value === 'string' || Number.isFinite(value);

export async function loadReleaseDiff(base, { signal, fetchImpl = fetch } = {}) {
  const indexResponse = await fetchImpl(`${base}/diffs/index.json`, { signal });
  if (indexResponse.status === 404) return { kind: 'unavailable' };
  if (!indexResponse.ok) throw new Error(`Release diff index request failed (${indexResponse.status})`);
  const index = await indexResponse.json();
  if (index?.policy_version !== 'release-diff-pages-v1' || !Array.isArray(index.diffs)) {
    throw new Error('Unsupported release diff index');
  }
  if (index.latest === null && index.diffs.length === 0) return { kind: 'unavailable' };

  const entry = index.diffs.find((item) => item?.path === index.latest);
  const { from, to, path } = entry || {};
  if (typeof from !== 'string' || typeof to !== 'string' || !VERSION.test(from) || !VERSION.test(to)
      || from >= to || to !== index.to || path !== `diffs/${from}--${to}.json`
      || entry.comparison_status !== VERIFIED) {
    throw new Error('Invalid published release pair');
  }
  const response = await fetchImpl(`${base}/${path}`, { signal });
  if (!response.ok) throw new Error(`Release diff request failed (${response.status})`);
  const report = await response.json();
  if (report?.policy_version !== 'release-diff-v1' || report.comparison_status !== VERIFIED
      || report.from?.dataset_version !== from || report.from.release_verified !== true
      || report.to?.dataset_version !== to || report.to.release_verified !== true
      || !Array.isArray(report.changes) || report.changes.length !== entry.changes
      || report.changes.length !== report.counts?.changes
      || report.changes.some((change) => typeof change?.code !== 'string' || !CODE.test(change.code)
        || !Object.hasOwn(RELEASE_DIFF_EVENTS, change.event) || !isValue(change.old_value) || !isValue(change.new_value))) {
    throw new Error('Inconsistent verified release report');
  }
  return { kind: 'ready', from, to, path, report };
}
