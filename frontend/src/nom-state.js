// Which of the Annex 2.4.1 states the record page must show for one code. Every state is explicit:
// a missing or unrecognised annex status is "unknown", never "no NOM applies".
export const NOM_STATES = Object.freeze(['listed', 'not_listed', 'not_listed_carried', 'unavailable', 'unknown', 'not_a_fraction']);

export function nomAnnexState(regulations, code) {
  const digits = String(code || '').replace(/\D/g, '');
  if (digits.length < 8) return 'not_a_fraction';
  const requirements = regulations?.requirements || [];
  const status = regulations?.annex?.status;
  if (requirements.length > 0) return 'listed';
  if (status === 'available') return 'not_listed';
  if (status === 'carried_forward') return 'not_listed_carried';
  if (status === 'unavailable') return 'unavailable';
  return 'unknown';
}
