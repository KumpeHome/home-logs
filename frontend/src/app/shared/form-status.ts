import { Component, input } from '@angular/core';

@Component({
  selector: 'hl-form-status',
  template: `
    @if (busy()) {
      <p class="form-status busy" data-test="form-busy" role="status">
        <span class="form-spinner" aria-hidden="true"></span>
        {{ busyLabel() }}
      </p>
    } @else if (success(); as message) {
      <p class="form-status success" data-test="form-success" role="status">{{ message }}</p>
    } @else if (error(); as message) {
      <p class="form-status error" data-test="form-error" role="alert">{{ message }}</p>
    }
  `,
  styles: `
    :host {
      display: block;
    }

    .form-status {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin: 0;
      font-weight: 600;
    }

    .form-status.busy {
      color: var(--kh-primary);
    }

    .form-status.success {
      color: var(--kh-success);
    }

    .form-status.error {
      color: var(--kh-danger);
    }

    .form-spinner {
      width: 1rem;
      height: 1rem;
      border: 2px solid var(--kh-border);
      border-top-color: var(--kh-primary);
      border-radius: 50%;
      animation: form-spin 0.7s linear infinite;
    }

    @keyframes form-spin {
      to {
        transform: rotate(360deg);
      }
    }
  `,
})
export class FormStatus {
  readonly busy = input(false);
  readonly success = input<string | null>(null);
  readonly error = input<string | null>(null);
  readonly busyLabel = input('Saving…');
}
