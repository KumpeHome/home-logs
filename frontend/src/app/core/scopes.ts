export const SCOPE_PREFIX = 'homelogs:';

export const HOUSEHOLD_READ = `${SCOPE_PREFIX}household:read`;
export const HOUSEHOLD_MANAGE = `${SCOPE_PREFIX}household:manage`;
export const MEMBERS_READ = `${SCOPE_PREFIX}members:read`;
export const MEMBERS_MANAGE = `${SCOPE_PREFIX}members:manage`;
export const MEMBERS_INVITE = `${SCOPE_PREFIX}members:invite`;
export const PROFILES_READ = `${SCOPE_PREFIX}profiles:read`;
export const PROFILES_WRITE = `${SCOPE_PREFIX}profiles:write`;
export const LOGS_READ = `${SCOPE_PREFIX}logs:read`;
export const LOGS_WRITE = `${SCOPE_PREFIX}logs:write`;
export const LOGS_AMEND = `${SCOPE_PREFIX}logs:amend`;
export const LOGS_EXPORT = `${SCOPE_PREFIX}logs:export`;
export const FORMS_MANAGE_TEMPLATES = `${SCOPE_PREFIX}forms:managetemplates`;
export const EDUCATION_READ = `${SCOPE_PREFIX}education:read`;
export const EDUCATION_WRITE = `${SCOPE_PREFIX}education:write`;
export const DISCIPLINE_READ = `${SCOPE_PREFIX}discipline:read`;
export const DISCIPLINE_WRITE = `${SCOPE_PREFIX}discipline:write`;
export const DOCUMENTS_READ = `${SCOPE_PREFIX}documents:read`;
export const DOCUMENTS_WRITE = `${SCOPE_PREFIX}documents:write`;
export const ADMIN_AUDIT = `${SCOPE_PREFIX}admin:audit`;

export const ALL_SCOPES: readonly string[] = [
  HOUSEHOLD_READ,
  HOUSEHOLD_MANAGE,
  MEMBERS_READ,
  MEMBERS_MANAGE,
  MEMBERS_INVITE,
  PROFILES_READ,
  PROFILES_WRITE,
  LOGS_READ,
  LOGS_WRITE,
  LOGS_AMEND,
  LOGS_EXPORT,
  FORMS_MANAGE_TEMPLATES,
  EDUCATION_READ,
  EDUCATION_WRITE,
  DISCIPLINE_READ,
  DISCIPLINE_WRITE,
  DOCUMENTS_READ,
  DOCUMENTS_WRITE,
  ADMIN_AUDIT,
];

export function parseHomelogsScopes(claim: string | string[] | null | undefined): string[] {
  if (!claim) {
    return [];
  }
  const tokens = typeof claim === 'string' ? claim.split(/\s+/) : claim;
  return tokens
    .map((token) => token.toLowerCase())
    .filter((token) => token.startsWith(SCOPE_PREFIX) && !token.includes('.'));
}

export function hasScope(scopes: readonly string[], needed: string): boolean {
  return scopes.includes(needed);
}

export function requestedOidcScopes(
  identityScopes: string,
  rbacScopes: readonly string[] = ALL_SCOPES,
): string {
  const tokens: string[] = [];
  const seen = new Set<string>();
  for (const token of [...identityScopes.split(/\s+/), ...rbacScopes]) {
    if (token && !seen.has(token)) {
      seen.add(token);
      tokens.push(token);
    }
  }
  return tokens.join(' ');
}
