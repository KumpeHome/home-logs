import {
  ALL_SCOPES,
  FORMS_MANAGE_TEMPLATES,
  HOUSEHOLD_READ,
  SCOPE_PREFIX,
  hasScope,
  parseHomelogsScopes,
  requestedOidcScopes,
} from './scopes';

describe('homelogs RBAC scopes', () => {
  it('uses lowercase colon-separated names', () => {
    expect(SCOPE_PREFIX).toBe('homelogs:');
    expect(HOUSEHOLD_READ).toBe('homelogs:household:read');
    expect(FORMS_MANAGE_TEMPLATES).toBe('homelogs:forms:managetemplates');
    expect(ALL_SCOPES.every((scope) => scope === scope.toLowerCase())).toBe(true);
    expect(ALL_SCOPES.every((scope) => !scope.includes('.'))).toBe(true);
    expect(ALL_SCOPES.every((scope) => scope.startsWith(SCOPE_PREFIX))).toBe(true);
  });

  it('keeps only homelogs prefixed scopes', () => {
    expect(parseHomelogsScopes('openid homelogs:logs:read email')).toEqual([
      'homelogs:logs:read',
    ]);
  });

  it('normalizes scope case from the token', () => {
    expect(parseHomelogsScopes('openid HOMELOGS:LOGS:READ')).toEqual(['homelogs:logs:read']);
  });

  it('checks required scope membership', () => {
    expect(hasScope(['homelogs:logs:write'], 'homelogs:logs:write')).toBe(true);
    expect(hasScope(['homelogs:logs:read'], 'homelogs:logs:write')).toBe(false);
  });

  it('includes RBAC scopes in the OIDC authorize request', () => {
    const requested = requestedOidcScopes('openid profile email offline_access').split(' ');
    expect(requested.slice(0, 4)).toEqual(['openid', 'profile', 'email', 'offline_access']);
    expect(ALL_SCOPES.every((scope) => requested.includes(scope))).toBe(true);
  });
});
