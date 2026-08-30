export const environment = {
  apiUrl: '/api',
  oidcIssuer: 'http://localhost:3301',
  oidcClientId: 'home-logs-spa',
  oidcAudience: 'https://homelogs.app/api',
  oidcScopes: 'openid profile email offline_access',
  /** Local SPA flag. The API also reports this via GET /api/health when AUTH_DISABLED=true. */
  authBypass: false,
};
