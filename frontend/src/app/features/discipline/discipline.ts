import { Component, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';

@Component({
  selector: 'hl-discipline',
  imports: [DatePipe, FormsModule],
  template: `
    <header class="page-head">
      <div>
        <p class="eyebrow">Care</p>
        <h1>Behavior notes</h1>
        <p class="lede">A respectful place to write down what happened, what helped, and what to try next.</p>
      </div>
      @if (!adding()) {
        <button class="hl-btn" type="button" (click)="adding.set(true)">Add a note</button>
      }
    </header>
    @if (adding()) {
    <section class="hl-card">
      <div class="head">
        <h2>What happened</h2>
        <button class="hl-btn ghost" type="button" (click)="adding.set(false)">Cancel</button>
      </div>
      <form class="hl-form" (ngSubmit)="save()">
        <label>Who
          <select [(ngModel)]="draft.member_id" name="mid">
            @for (member of members(); track member.id) {
              <option [value]="member.id">{{ member.legal_name }}</option>
            }
          </select>
        </label>
        <label>Where <input [(ngModel)]="draft.location" name="loc" /></label>
        <label>What was going on beforehand <textarea [(ngModel)]="draft.antecedent" name="ant"></textarea></label>
        <label>What happened <textarea [(ngModel)]="draft.behavior" name="beh"></textarea></label>
        <label>What helped <textarea [(ngModel)]="draft.intervention" name="int"></textarea></label>
        <label>What followed <textarea [(ngModel)]="draft.consequence" name="con"></textarea></label>
        <label>How long (minutes) <input type="number" [(ngModel)]="draft.duration_minutes" name="dur" /></label>
        <label>Follow-up <textarea [(ngModel)]="draft.follow_up" name="fu"></textarea></label>
        <label>People notified (comma separated) <input [(ngModel)]="notified" name="note" /></label>
        <button class="hl-btn">Save notes</button>
      </form>
    </section>
    }
    @if (rows().length) {
      <div class="table-wrap">
        <table>
          <tr><th>When</th><th>What happened</th><th>What helped</th><th>Follow-up</th></tr>
          @for (row of rows(); track row.id) {
            <tr>
              <td>{{ row.occurred_at | date:'short' }}</td>
              <td>{{ row.behavior }}</td>
              <td>{{ row.intervention }}</td>
              <td>{{ row.follow_up }}</td>
            </tr>
          }
        </table>
      </div>
    } @else if (!adding()) {
      <section class="hl-card">
        <div class="empty">
          <strong>No behavior notes yet</strong>
          <span>When something is worth remembering, add a short note. Keep the language factual and kind.</span>
        </div>
      </section>
    }
  `,
})
export class DisciplinePage {
  private readonly api = inject(ApiService);
  readonly members = signal<any[]>([]);
  readonly rows = signal<any[]>([]);
  readonly adding = signal(false);
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
    }).subscribe(() => {
      this.adding.set(false);
      this.reload();
    });
  }
}
