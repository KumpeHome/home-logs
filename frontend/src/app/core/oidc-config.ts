export type PublicOidcConfig = {
  issuer: string;
  clientId: string;
  audience: string;
  scopes: string;
};

export type RuntimeOidcEnv = {
  OIDC_ISSUER?: string;
  OIDC_CLIENT_ID?: string;
  OIDC_AUDIENCE?: string;
  OIDC_SCOPES?: string;
};

export function resolveOidcConfig(
  defaults: PublicOidcConfig,
  runtime?: RuntimeOidcEnv | null,
): PublicOidcConfig {
  return {
    issuer: runtime?.OIDC_ISSUER || defaults.issuer,
    clientId: runtime?.OIDC_CLIENT_ID || defaults.clientId,
    audience: runtime?.OIDC_AUDIENCE || defaults.audience,
    scopes: runtime?.OIDC_SCOPES || defaults.scopes,
  };
}

export function runtimeOidcEnv(
  win: Window & { __ENV__?: RuntimeOidcEnv } = window,
): RuntimeOidcEnv {
  return win.__ENV__ ?? {};
}
