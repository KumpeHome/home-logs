import { Component, inject } from '@angular/core';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'hl-login',
  template: `
    <section class="login hl-card">
      <img src="assets/brand/logo.svg" width="72" height="72" alt="Home Logs" />
      <h1>Home Logs</h1>
      <p class="muted">Household and foster-care logging, signed in with KumpeCloud Auth.</p>
      <button class="hl-btn" (click)="auth.login()">Sign in</button>
      @if (auth.bypassAvailable()) {
        <p class="muted">OIDC bypass is on (AUTH_DISABLED). Sign in skips the identity provider.</p>
      }
    </section>
  `,
  styles: `
    .login {
      max-width: 420px;
      margin: 12vh auto;
      text-align: center;
      display: grid;
      gap: 0.75rem;
      justify-items: center;
    }
  `,
})
export class LoginPage {
  readonly auth = inject(AuthService);
}
