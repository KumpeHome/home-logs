export type FieldSpec = {
  title?: string;
  type?: string;
  format?: string;
  enum?: string[];
  'x-widget'?: string;
};

export const ARRAY_WIDGETS = new Set([
  'member-checkboxes',
  'member-multiselect',
  'child-multiselect',
]);

export function resolveFormWidget(key: string, spec: FieldSpec): string {
  if (spec['x-widget']) {
    return spec['x-widget'];
  }
  if (spec.format === 'member-ids' || (spec.type === 'array' && key === 'participants')) {
    return 'member-multiselect';
  }
  if (spec.format === 'child-ids') {
    return 'child-multiselect';
  }
  if (spec.type === 'array') {
    return 'comma-list';
  }
  if (spec.enum) {
    return 'select';
  }
  if (spec.format === 'date') {
    return 'date';
  }
  if (spec.format === 'date-time') {
    return 'datetime-local';
  }
  if (spec.format === 'time') {
    return 'time';
  }
  if (spec.type === 'boolean') {
    return 'boolean';
  }
  if (spec.type === 'integer') {
    return 'number';
  }
  if (spec.type === 'string' && key.includes('notes')) {
    return 'textarea';
  }
  return 'text';
}
