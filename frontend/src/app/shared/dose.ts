export const DOSE_UNITS = [
  'mg',
  'mcg',
  'g',
  'mL',
  'IU',
  'units',
  'tablet',
  'capsule',
  'drop',
  'puff',
] as const;

export type DoseUnit = (typeof DOSE_UNITS)[number];

const DOSE_RE = /^\s*(\d+(?:\.\d+)?)\s*([A-Za-zµμ]+)?\s*$/;

function trimAmount(value: number): string {
  if (!Number.isFinite(value)) {
    return '';
  }
  return String(Number(value.toPrecision(12)));
}

export function parseDose(value: string | null | undefined): { amount: string | null; unit: string } {
  const text = (value ?? '').trim();
  if (!text) {
    return { amount: null, unit: 'mg' };
  }
  const match = DOSE_RE.exec(text);
  if (!match) {
    return { amount: null, unit: 'mg' };
  }
  return { amount: trimAmount(Number(match[1])), unit: match[2] || 'mg' };
}

export function composeDose(amount: string | number | null | undefined, unit: string | null | undefined): string {
  const text = String(amount ?? '').trim();
  if (!text) {
    return '';
  }
  const numeric = Number(text);
  const trimmed = Number.isFinite(numeric) ? trimAmount(numeric) : text;
  const suffix = (unit ?? 'mg').trim() || 'mg';
  return `${trimmed}${suffix}`;
}

export function administeredDose(unitDose: string | null | undefined, quantity: number | string | null | undefined): string {
  const parsed = parseDose(unitDose);
  if (parsed.amount === null) {
    return (unitDose ?? '').trim();
  }
  const qty = Number(quantity === null || quantity === undefined || quantity === '' ? 1 : quantity);
  const safeQty = Number.isFinite(qty) && qty > 0 ? qty : 1;
  return composeDose(Number(parsed.amount) * safeQty, parsed.unit);
}
