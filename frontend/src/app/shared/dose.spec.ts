import { administeredDose, composeDose, parseDose } from './dose';

describe('dose helpers', () => {
  it('multiplies unit strength by the number given', () => {
    expect(administeredDose('1mg', 2)).toBe('2mg');
    expect(administeredDose('1.5 mg', 2)).toBe('3mg');
  });

  it('composes and parses amount plus unit', () => {
    expect(composeDose('1', 'mg')).toBe('1mg');
    expect(parseDose('5mg')).toEqual({ amount: '5', unit: 'mg' });
  });
});
