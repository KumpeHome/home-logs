import { flagLabel, isAdministerable, MEDICATION_FLAGS } from './medication';

describe('medication helpers', () => {
  it('hides meds outside their start and end dates', () => {
    expect(
      isAdministerable({
        active: true,
        start_date: '2026-01-01',
        end_date: '2026-01-31',
      }, '2026-08-19'),
    ).toBe(false);
    expect(
      isAdministerable({
        active: true,
        start_date: '2026-01-01',
        end_date: null,
      }, '2026-08-19'),
    ).toBe(true);
  });

  it('includes awareness flags such as drowsy and take with food', () => {
    const codes = MEDICATION_FLAGS.map((item) => item.code);
    expect(codes).toContain('drowsy');
    expect(codes).toContain('take_with_food');
    expect(flagLabel('drowsy')).toBe('Drowsy');
    expect(flagLabel('take_with_food')).toBe('Take with food');
  });
});
