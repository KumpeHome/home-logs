import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'hl-dashboard',
  imports: [DatePipe, FormsModule, RouterLink],
  template: `
    <h1>Dashboard</h1>
    @if (!auth.householdId()) {
      <section class="hl-card">
        <h2>Create your first household</h2>
        <form class="hl-form" (ngSubmit)="createHome()">
          <label>Name <input [(ngModel)]="homeName" name="hname" /></label>
          <label>Type
            <select [(ngModel)]="homeType" name="htype">
              <option value="family">Family</option>
              <option value="foster">Foster</option>
              <option value="mixed">Mixed</option>
            </select>
          </label>
          <button class="hl-btn">Create household</button>
        </form>
      </section>
    }
    @if (data(); as dash) {
      <div class="hl-grid stats">
        <article class="hl-card"><strong>{{ dash.active_members }}</strong><span>Active members</span></article>
        <article class="hl-card"><strong>{{ dash.inactive_members }}</strong><span>Inactive</span></article>
        <article class="hl-card"><strong>{{ dash.drafts }}</strong><span>Draft logs</span></article>
        <article class="hl-card"><strong>{{ dash.meds_due.length }}</strong><span>Meds due</span></article>
      </div>
      <section class="hl-card">
        <h2>Medications due</h2>
        @for (med of dash.meds_due; track med.medication_id + med.scheduled_time) {
          <p>{{ med.member_name }} — {{ med.medication_name }} {{ med.dose }} at {{ med.scheduled_time }}</p>
        } @empty {
          <p class="muted">No scheduled medications waiting.</p>
        }
      </section>
      <section class="hl-card">
        <h2>Recent logs</h2>
        <table>
          <tr><th>When</th><th>Form</th><th>Who</th><th>Status</th><th></th></tr>
          @for (log of dash.recent_logs; track log.id) {
            <tr>
              <td>{{ log.occurred_at | date: 'short':timezone() }}</td>
              <td>{{ log.form_name }}</td>
              <td>{{ log.subject_name || 'Household' }}</td>
              <td><span class="hl-pill active">{{ log.status }}</span></td>
              <td><a class="hl-btn secondary" [routerLink]="['/forms', log.id]">View</a></td>
            </tr>
          }
        </table>
      </section>
    }
  `,
  styles: `
    .stats { grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); }
    .stats strong { font-size: 1.8rem; display: block; }
  `,
})
export class DashboardPage {
  private readonly api = inject(ApiService);
  readonly auth = inject(AuthService);
  readonly data = signal<any>(null);
  homeName = 'Our Home';
  homeType = 'foster';

  constructor() {
    this.refresh();
  }

  refresh(): void {
    const id = this.auth.householdId();
    if (id) {
      this.api.get(`/households/${id}/dashboard`).subscribe((value) => this.data.set(value));
    }
  }

  timezone(): string {
    return this.api.timezone();
  }

  createHome(): void {
    this.api
      .post<{ id: string }>('/households', {
        name: this.homeName,
        household_type: this.homeType,
      })
      .subscribe((row) => {
        this.auth.selectHousehold(row.id);
        this.refresh();
      });
  }
}
