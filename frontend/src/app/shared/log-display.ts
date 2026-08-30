export type FormSchema = {
  properties?: Record<string, { title?: string; type?: string }>;
};

export type NamedMember = { id: string; legal_name: string };

export function formatFieldValue(value: unknown, members: NamedMember[] = []): string {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  if (Array.isArray(value)) {
    if (!value.length) {
      return '—';
    }
    return value.map((item) => formatFieldValue(item, members)).join(', ');
  }
  if (typeof value === 'string') {
    if (value.startsWith('data:image')) {
      return 'Signed';
    }
    return members.find((member) => member.id === value)?.legal_name ?? value;
  }
  return String(value);
}

export type SubmissionField = {
  key: string;
  title: string;
  value: string;
  imageUrl?: string;
};

export function submissionFields(
  schema: FormSchema | undefined,
  payload: Record<string, unknown> | undefined,
  members: NamedMember[] = [],
): SubmissionField[] {
  const properties = schema?.properties ?? {};
  const data = payload ?? {};
  const keys = [
    ...Object.keys(properties),
    ...Object.keys(data).filter((key) => !(key in properties)),
  ];
  return keys.map((key) => {
    const raw = data[key];
    const imageUrl = typeof raw === 'string' && raw.startsWith('data:image') ? raw : undefined;
    return {
      key,
      title: properties[key]?.title ?? key.replaceAll('_', ' '),
      value: formatFieldValue(raw, members),
      ...(imageUrl ? { imageUrl } : {}),
    };
  });
}
