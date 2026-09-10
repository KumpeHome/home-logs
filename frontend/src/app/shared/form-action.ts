import { signal } from '@angular/core';
import type { Observable } from 'rxjs';

export type FormRequestError = { error?: { detail?: unknown } };

export function formErrorMessage(
  err: FormRequestError,
  fallback = 'Could not save. Try again.',
): string {
  const detail = err.error?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }
  return fallback;
}

export class FormAction {
  readonly busy = signal(false);
  readonly success = signal<string | null>(null);
  readonly error = signal<string | null>(null);

  begin(): void {
    this.busy.set(true);
    this.success.set(null);
    this.error.set(null);
  }

  succeed(message: string): void {
    this.busy.set(false);
    this.success.set(message);
    this.error.set(null);
  }

  fail(message: string): void {
    this.busy.set(false);
    this.success.set(null);
    this.error.set(message);
  }

  clear(): void {
    this.busy.set(false);
    this.success.set(null);
    this.error.set(null);
  }

  run<T>(request: Observable<T>, successMessage: string, onSuccess?: (value: T) => void): void {
    this.begin();
    request.subscribe({
      next: (value) => {
        this.succeed(successMessage);
        onSuccess?.(value);
      },
      error: (err: FormRequestError) => {
        this.fail(formErrorMessage(err));
      },
    });
  }
}
