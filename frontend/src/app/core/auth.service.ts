import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { environment } from './environment';
import { parseHomelogsScopes, requestedOidcScopes } from './scopes';
import { shouldBypassOidc } from './auth-bypass';

export type PermissionGrant = { resource: string; action: string };

export type HouseholdSummary = {
  id: string;
  name: string;
  household_type: string;
  timezone: string;
  member_id?: string | null;
  household_role?: string | null;
  permissions?: PermissionGrant[];
};

export interface MeResponse {
  subject: string;
  email: string | null;
  name: string | null;
  scopes: string[];
  linked: boolean;
  pending_memberships: { household_id: string; member_id: string }[];
  households: HouseholdSummary[];
}

const TOKEN_KEY = 'homelogs.access_token';
const HOUSEHOLD_KEY = 'homelogs.household';

function readStore(kind: 'session' | 'local', key: string): string | null {
  try {
    const store = kind === 'session' ? globalThis.sessionStorage : globalThis.localStorage;
    return store?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

function writeStore(kind: 'session' | 'local', key: string, value: string | null): void {
  try {
    const store = kind === 'session' ? globalThis.sessionStorage : globalThis.localStorage;
    if (!store) {
      return;
    }
    if (value === null) {
      store.removeItem(key);
    } else {
      store.setItem(key, value);
    }
  } catch {
    /* ignore missing web storage in tests */
  }
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  readonly me = signal<MeResponse | null>(null);
  readonly token = signal<string | null>(readStore('session', TOKEN_KEY));
  readonly householdId = signal<string | null>(readStore('local', HOUSEHOLD_KEY));
  readonly bypassAvailable = signal(false);

  scopes(): string[] {
    return this.me()?.scopes ?? [];
  }

  has(scope: string): boolean {
    return this.scopes().includes(scope);
  }

  currentHousehold(): HouseholdSummary | undefined {
    const id = this.householdId();
    return this.me()?.households.find((item) => item.id === id) ?? this.me()?.households[0];
  }

  isHouseholdAdmin(): boolean {
    return this.currentHousehold()?.household_role === 'admin';
  }

  can(resource: string, action: string): boolean {
    const home = this.currentHousehold();
    if (!home) {
      return true;
    }
    if (home.household_role === 'admin') {
      return true;
    }
    if (!home.permissions) {
      return true;
    }
    return home.permissions.some((grant) => grant.resource === resource && grant.action === action);
  }

  async bootstrap(): Promise<void> {
    if (await this.enterBypassIfEnabled()) {
      return;
    }
    if (window.location.pathname === '/callback') {
      await this.handleCallback();
      return;
    }
    if (this.token()) {
      await this.loadMe();
    }
  }

  async login(): Promise<void> {
    if (await this.enterBypassIfEnabled()) {
      return;
    }
    const verifier = this.randomString(64);
    const challenge = await this.pkceChallenge(verifier);
    const state = this.randomString(24);
    writeStore('session', 'oidc.verifier', verifier);
    writeStore('session', 'oidc.state', state);
    const url = new URL(`${environment.oidcIssuer.replace(/\/$/, '')}/oidc/auth`);
    url.searchParams.set('client_id', environment.oidcClientId);
    url.searchParams.set('redirect_uri', `${window.location.origin}/callback`);
    url.searchParams.set('response_type', 'code');
    url.searchParams.set('scope', requestedOidcScopes(environment.oidcScopes));
    url.searchParams.set('code_challenge', challenge);
    url.searchParams.set('code_challenge_method', 'S256');
    url.searchParams.set('state', state);
    url.searchParams.set('resource', environment.oidcAudience);
    window.location.assign(url.toString());
  }

  async handleCallback(): Promise<void> {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');
    if (!code || state !== readStore('session', 'oidc.state')) {
      await this.router.navigateByUrl('/login');
      return;
    }
    const body = new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: environment.oidcClientId,
      code,
      redirect_uri: `${window.location.origin}/callback`,
      code_verifier: readStore('session', 'oidc.verifier') ?? '',
      resource: environment.oidcAudience,
    });
    const tokenUrl = `${environment.oidcIssuer.replace(/\/$/, '')}/oidc/token`;
    const response = await fetch(tokenUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
    if (!response.ok) {
      await this.router.navigateByUrl('/login');
      return;
    }
    const payload = (await response.json()) as { access_token: string; scope?: string };
    this.setToken(payload.access_token);
    if (payload.scope) {
      parseHomelogsScopes(payload.scope);
    }
    await this.loadMe();
    await this.router.navigateByUrl('/');
  }

  logout(): void {
    writeStore('session', TOKEN_KEY, null);
    this.token.set(null);
    this.me.set(null);
    void this.router.navigateByUrl('/login');
  }

  selectHousehold(id: string): void {
    writeStore('local', HOUSEHOLD_KEY, id);
    this.householdId.set(id);
  }

  householdTimezone(): string {
    const id = this.householdId();
    const match = this.me()?.households.find((item) => item.id === id);
    return match?.timezone || 'America/Chicago';
  }

  private setToken(token: string): void {
    writeStore('session', TOKEN_KEY, token);
    this.token.set(token);
  }

  private async enterBypassIfEnabled(): Promise<boolean> {
    let healthBypass = false;
    try {
      const response = await fetch(`${environment.apiUrl}/health`);
      if (response.ok) {
        const body = (await response.json()) as { auth_bypass?: boolean };
        healthBypass = body.auth_bypass === true;
      }
    } catch {
      healthBypass = false;
    }
    this.bypassAvailable.set(shouldBypassOidc(environment.authBypass, healthBypass));
    if (!this.bypassAvailable()) {
      return false;
    }
    this.setToken('dev-bypass');
    await this.loadMe();
    if (window.location.pathname === '/login' || window.location.pathname === '/callback') {
      await this.router.navigateByUrl('/');
    }
    return true;
  }

  private async loadMe(): Promise<void> {
    try {
      const me = await firstValueFrom(
        this.http.get<MeResponse>(`${environment.apiUrl}/me`),
      );
      this.me.set(me ?? null);
      if (me && !me.linked && !this.bypassAvailable()) {
        await this.router.navigateByUrl('/pending');
        return;
      }
      if (me && !this.householdId() && me.households[0]) {
        this.selectHousehold(me.households[0].id);
      }
    } catch {
      this.me.set(null);
    }
  }

  private randomString(length: number): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
    const bytes = crypto.getRandomValues(new Uint8Array(length));
    return Array.from(bytes, (b) => chars[b % chars.length]).join('');
  }

  private async pkceChallenge(verifier: string): Promise<string> {
    const data = new TextEncoder().encode(verifier);
    const digest = await crypto.subtle.digest('SHA-256', data);
    return btoa(String.fromCharCode(...new Uint8Array(digest)))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '');
  }
}
