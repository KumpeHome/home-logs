export type MedFlag = {
  code: string;
  label: string;
};

export const MEDICATION_FLAGS: MedFlag[] = [
  { code: 'drowsy', label: 'Drowsy' },
  { code: 'take_with_food', label: 'Take with food' },
  { code: 'empty_stomach', label: 'Empty stomach' },
  { code: 'avoid_alcohol', label: 'Avoid alcohol' },
  { code: 'dizziness', label: 'May cause dizziness' },
  { code: 'photosensitivity', label: 'Photosensitivity' },
  { code: 'refrigerate', label: 'Refrigerate' },
  { code: 'shake_well', label: 'Shake well' },
  { code: 'do_not_crush', label: 'Do not crush' },
  { code: 'with_water', label: 'Take with water' },
];

export function flagLabel(code: string): string {
  return MEDICATION_FLAGS.find((item) => item.code === code)?.label ?? code;
}

export type AdministerableMed = {
  id: string;
  name: string;
  dose?: string;
  active?: boolean;
  start_date?: string | null;
  end_date?: string | null;
  flags?: string[];
  is_otc?: boolean;
  otc_medication_id?: string;
};

export function isAdministerable(
  med: {
    active?: boolean;
    start_date?: string | null;
    end_date?: string | null;
  },
  on: string = todayIso(),
): boolean {
  if (med.active === false) {
    return false;
  }
  if (med.start_date && on < med.start_date) {
    return false;
  }
  if (med.end_date && on > med.end_date) {
    return false;
  }
  return true;
}

export function administerableChoices(
  profile: {
    medications?: AdministerableMed[];
    otc_medications?: AdministerableMed[];
  },
  catalog: AdministerableMed[] = [],
  on: string = todayIso(),
): AdministerableMed[] {
  const prescribed = (profile.medications ?? []).filter((item) => isAdministerable(item, on));
  const assigned = (profile.otc_medications ?? []).filter((item) => isAdministerable(item, on));
  const assignedIds = new Set(assigned.map((item) => item.otc_medication_id));
  const household = catalog
    .filter((item) => item.active !== false && !assignedIds.has(item.id))
    .map((item) => ({ ...item, is_otc: true }));
  return [...prescribed, ...assigned, ...household];
}

function todayIso(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}
