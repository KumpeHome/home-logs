import { administerableChoices, flagLabel, isAdministerable, MEDICATION_FLAGS } from './medication';

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

  it('includes household cabinet OTCs that are not assigned to the member', () => {
    const rows = administerableChoices(
      { medications: [], otc_medications: [] },
      [{ id: 'otc1', name: 'Acetaminophen', dose: '325mg', active: true }],
    );
    expect(rows.map((item) => item.name)).toContain('Acetaminophen');
    expect(rows[0].id).toBe('otc1');
    expect(rows[0].is_otc).toBe(true);
  });

  it('keeps assigned OTC ids instead of duplicating the cabinet item', () => {
    const rows = administerableChoices(
      {
        medications: [],
        otc_medications: [
          {
            id: 'as1',
            otc_medication_id: 'otc1',
            name: 'Acetaminophen',
            dose: '500mg',
            active: true,
            is_otc: true,
          },
        ],
      },
      [{ id: 'otc1', name: 'Acetaminophen', dose: '325mg', active: true }],
    );
    expect(rows).toHaveLength(1);
    expect(rows[0].id).toBe('as1');
    expect(rows[0].dose).toBe('500mg');
  });
});
