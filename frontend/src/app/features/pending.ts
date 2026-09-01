import { Component, inject } from '@angular/core';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'hl-pending',
  template: `
    <section class="auth-screen">
      <div class="hl-card auth-card">
        <img class="brand-logo" src="assets/brand/logo.webp" width="160" alt="Kumpe Home Logs" />
        <h1>You're almost in</h1>
        <p class="lede">
          This login is recognized, and a household admin still needs to invite this email.
          After that invite, the next sign-in links you to the home.
        </p>
        <button class="hl-btn secondary" (click)="auth.logout()">Sign out</button>
      </div>
    </section>
  `,
})
export class PendingPage {
  readonly auth = inject(AuthService);
}
