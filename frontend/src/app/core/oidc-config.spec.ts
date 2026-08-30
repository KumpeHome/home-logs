import { resolveOidcConfig } from './oidc-config';

const baked = {
  issuer: 'http://localhost:3301',
  clientId: 'home-logs-spa',
  audience: 'https://homelogs.app/api',
  scopes: 'openid profile email offline_access',
};

describe('resolveOidcConfig', () => {
  it('prefers OIDC values from container env over baked localhost defaults', () => {
    const resolved = resolveOidcConfig(baked, {
      OIDC_ISSUER: 'https://auth.stage.kumpe.app',
      OIDC_CLIENT_ID: 'home-logs-spa-stage',
      OIDC_AUDIENCE: 'https://homelogs.app/api',
    });
    expect(resolved.issuer).toBe('https://auth.stage.kumpe.app');
    expect(resolved.clientId).toBe('home-logs-spa-stage');
    expect(resolved.audience).toBe('https://homelogs.app/api');
  });

  it('keeps baked defaults when runtime env is empty', () => {
    expect(resolveOidcConfig(baked, {})).toEqual(baked);
    expect(resolveOidcConfig(baked, null)).toEqual(baked);
  });
});
