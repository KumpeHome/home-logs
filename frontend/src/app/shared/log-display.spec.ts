import { formatFieldValue, submissionFields } from './log-display';

describe('log display', () => {
  it('labels payload fields from the form schema and resolves member ids', () => {
    const fields = submissionFields(
      {
        properties: {
          date: { title: 'Date', type: 'string' },
          participants: { title: 'Members participating', type: 'array' },
          evacuation_seconds: { title: 'Seconds to evacuate', type: 'integer' },
        },
      },
      {
        date: '2026-08-19',
        participants: ['m1', 'm2'],
        evacuation_seconds: 47,
      },
      [
        { id: 'm1', legal_name: 'Ada Admin' },
        { id: 'm2', legal_name: 'Casey Child' },
      ],
    );
    expect(fields).toEqual([
      { key: 'date', title: 'Date', value: '2026-08-19' },
      { key: 'participants', title: 'Members participating', value: 'Ada Admin, Casey Child' },
      { key: 'evacuation_seconds', title: 'Seconds to evacuate', value: '47' },
    ]);
  });

  it('renders booleans as Yes/No', () => {
    expect(formatFieldValue(true, [])).toBe('Yes');
    expect(formatFieldValue(false, [])).toBe('No');
  });

  it('shows drawn initials as Signed instead of a data URL', () => {
    expect(formatFieldValue('data:image/png;base64,abc', [])).toBe('Signed');
  });

  it('exposes drawn initials as an image url for display', () => {
    const fields = submissionFields(
      { properties: { fp_initials: { title: 'Foster parent initials' } } },
      { fp_initials: 'data:image/png;base64,abc' },
    );
    expect(fields[0].imageUrl).toBe('data:image/png;base64,abc');
  });
});
