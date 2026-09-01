export function firstName(name: string | null | undefined): string {
  const trimmed = name?.trim() ?? '';
  if (!trimmed) {
    return 'there';
  }
  return trimmed.split(/\s+/)[0] ?? 'there';
}

export function timeOfDayGreeting(hour: number, name: string | null | undefined): string {
  const who = firstName(name);
  if (hour < 12) {
    return `Good morning, ${who}`;
  }
  if (hour < 17) {
    return `Good afternoon, ${who}`;
  }
  return `Good evening, ${who}`;
}
