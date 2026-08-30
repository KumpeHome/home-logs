import { Component, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';

@Component({
  selector: 'hl-forms-archive',
  imports: [DatePipe, RouterLink],
  templateUrl: './archive.html',
  styleUrl: './archive.scss',
})
export class FormsArchivePage {
  private readonly api = inject(ApiService);
  readonly forms = signal<any[]>([]);
  readonly logs = signal<any[]>([]);
  readonly tab = signal<string>('');

  constructor() {
    this.api.get<any[]>('/form-types').subscribe((rows) => {
      this.forms.set(rows);
      const first = rows[0]?.code;
      if (first) {
        this.show(first);
      }
    });
  }

  show(code: string): void {
    this.tab.set(code);
    const hid = this.api.hid();
    if (!hid) {
      return;
    }
    this.api
      .get<any[]>(`/households/${hid}/logs?form_type_code=${encodeURIComponent(code)}`)
      .subscribe((rows) => this.logs.set(rows));
  }

  timezone(): string {
    return this.api.timezone();
  }

  selectedForm(): any {
    return this.forms().find((item) => item.code === this.tab());
  }
}
