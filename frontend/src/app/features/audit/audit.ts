import { Component, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ApiService } from '../../core/api.service';

@Component({
  selector: 'hl-audit',
  imports: [DatePipe],
  template: `
    <header class="page-head">
      <div>
        <p class="eyebrow">Records</p>
        <h1>Activity</h1>
        <p class="lede">A quiet history of who changed what, when you need it.</p>
      </div>
    </header>
    <div class="table-wrap">
    <table>
      <tr><th>When</th><th>Actor</th><th>Action</th><th>Summary</th></tr>
      @for (row of rows(); track row.id) {
        <tr>
          <td>{{ row.created_at | date:'short' }}</td>
          <td>{{ row.actor_email }}</td>
          <td>{{ row.action }} {{ row.entity_type }}</td>
          <td>{{ row.summary }}</td>
        </tr>
      }
    </table>
    </div>
  `,
})
export class AuditPage {
  private readonly api = inject(ApiService);
  readonly rows = signal<any[]>([]);

  constructor() {
    this.api.get<any[]>(`/households/${this.api.hid()}/audit`).subscribe((rows) => this.rows.set(rows));
  }
}
