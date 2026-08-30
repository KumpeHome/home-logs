import { shouldBypassOidc } from './auth-bypass';

describe('shouldBypassOidc', () => {
  it('is off unless the env flag or health payload says so', () => {
    expect(shouldBypassOidc(false, false)).toBe(false);
    expect(shouldBypassOidc(false, undefined)).toBe(false);
    expect(shouldBypassOidc(true, false)).toBe(true);
    expect(shouldBypassOidc(false, true)).toBe(true);
  });
});
