import { Component, inject } from '@angular/core';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'hl-pending',
  template: `
    <section class="hl-card" style="max-width:520px;margin:10vh auto">
      <h1>Account pending</h1>
      <p>Your login is recognized, but it is not linked to an active household membership yet. Ask a household admin to invite this email. The account stays pending until the first successful sign-in after that invite.</p>
      <button class="hl-btn secondary" (click)="auth.logout()">Sign out</button>
    </section>
  `,
})
export class PendingPage {
  readonly auth = inject(AuthService);
}
