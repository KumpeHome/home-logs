import { Component, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';

@Component({
  selector: 'hl-discipline',
  imports: [DatePipe, FormsModule],
  template: `
    <h1>Discipline</h1>
    <section class="hl-card">
      <form class="hl-form" (ngSubmit)="save()">
        <label>Member
          <select [(ngModel)]="draft.member_id" name="mid">
            @for (member of members(); track member.id) {
              <option [value]="member.id">{{ member.legal_name }}</option>
            }
          </select>
        </label>
        <label>Location <input [(ngModel)]="draft.location" name="loc" /></label>
        <label>Antecedent <textarea [(ngModel)]="draft.antecedent" name="ant"></textarea></label>
        <label>Behavior <textarea [(ngModel)]="draft.behavior" name="beh"></textarea></label>
        <label>Intervention <textarea [(ngModel)]="draft.intervention" name="int"></textarea></label>
        <label>Consequence <textarea [(ngModel)]="draft.consequence" name="con"></textarea></label>
        <label>Duration (min) <input type="number" [(ngModel)]="draft.duration_minutes" name="dur" /></label>
        <label>Follow-up <textarea [(ngModel)]="draft.follow_up" name="fu"></textarea></label>
        <label>Notified (comma) <input [(ngModel)]="notified" name="note" /></label>
        <button class="hl-btn">Record discipline</button>
      </form>
    </section>
    <table>
      <tr><th>When</th><th>Behavior</th><th>Intervention</th><th>Follow-up</th></tr>
      @for (row of rows(); track row.id) {
        <tr>
          <td>{{ row.occurred_at | date:'short' }}</td>
          <td>{{ row.behavior }}</td>
          <td>{{ row.intervention }}</td>
          <td>{{ row.follow_up }}</td>
        </tr>
      }
    </table>
  `,
})
export class DisciplinePage {
  private readonly api = inject(ApiService);
  readonly members = signal<any[]>([]);
  readonly rows = signal<any[]>([]);
  notified = '';
  draft: any = {
    member_id: '',
    location: 'Home',
    antecedent: '',
    behavior: '',
    intervention: '',
    consequence: '',
    duration_minutes: 10,
    follow_up: '',
  };

  constructor() {
    this.api.get<any[]>(`/households/${this.api.hid()}/members`).subscribe((rows) => {
      this.members.set(rows);
      this.draft.member_id = rows[0]?.id ?? '';
    });
    this.reload();
  }

  reload(): void {
    this.api.get<any[]>(`/households/${this.api.hid()}/discipline`).subscribe((rows) => this.rows.set(rows));
  }

  save(): void {
    this.api.post(`/households/${this.api.hid()}/discipline`, {
      ...this.draft,
      occurred_at: new Date().toISOString(),
      notified: this.notified.split(',').map((item) => item.trim()).filter(Boolean),
    }).subscribe(() => this.reload());
  }
}
