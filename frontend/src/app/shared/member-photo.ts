import { Component, OnDestroy, effect, inject, input, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../core/environment';

@Component({
  selector: 'hl-member-photo',
  template: `
    @if (src()) {
      <img class="hl-avatar" [class.large]="size() === 'lg'" [src]="src()" [alt]="name()" />
    } @else {
      <span
        class="hl-avatar placeholder"
        [class.large]="size() === 'lg'"
        [attr.aria-label]="name()"
      >{{ initials() }}</span>
    }
  `,
})
export class MemberPhoto implements OnDestroy {
  private readonly http = inject(HttpClient);
  private objectUrl: string | null = null;
  readonly householdId = input.required<string>();
  readonly memberId = input.required<string>();
  readonly name = input('');
  readonly hasPhoto = input(false);
  readonly size = input<'sm' | 'lg'>('sm');
  readonly src = signal<string | null>(null);

  constructor() {
    effect((onCleanup) => {
      const hasPhoto = this.hasPhoto();
      const householdId = this.householdId();
      const memberId = this.memberId();
      this.clearPhoto();
      if (!hasPhoto || !householdId || !memberId) {
        return;
      }
      const sub = this.http
        .get(`${environment.apiUrl}/households/${householdId}/members/${memberId}/photo`, {
          responseType: 'blob',
        })
        .subscribe({
          next: (blob) => this.setPhoto(blob),
          error: () => this.clearPhoto(),
        });
      onCleanup(() => {
        sub.unsubscribe();
        this.clearPhoto();
      });
    });
  }

  ngOnDestroy(): void {
    this.clearPhoto();
  }

  initials(): string {
    const parts = this.name().trim().split(/\s+/).filter(Boolean);
    if (!parts.length) {
      return '?';
    }
    return parts
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? '')
      .join('');
  }

  private setPhoto(blob: Blob): void {
    this.clearPhoto();
    this.objectUrl = URL.createObjectURL(blob);
    this.src.set(this.objectUrl);
  }

  private clearPhoto(): void {
    if (this.objectUrl) {
      URL.revokeObjectURL(this.objectUrl);
      this.objectUrl = null;
    }
    this.src.set(null);
  }
}
