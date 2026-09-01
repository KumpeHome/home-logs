import { Component, inject } from '@angular/core';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'hl-login',
  template: `
    <section class="auth-screen">
      <div class="hl-card auth-card">
        <img
          class="brand-logo"
          data-test="brand-logo"
          src="assets/brand/logo.webp"
          width="220"
          alt="Kumpe Home Logs"
        />
        <h1>Your home. Your records. One secure place.</h1>
        <p class="lede">
          A calm spot to keep up with the people, medications, school days, and
          everyday notes that make a household feel looked after.
        </p>
        <button class="hl-btn" (click)="auth.login()">Sign in</button>
        @if (auth.bypassAvailable()) {
          <p class="muted">OIDC bypass is on. Sign in skips the identity provider.</p>
        }
      </div>
    </section>
  `,
})
export class LoginPage {
  readonly auth = inject(AuthService);
}
