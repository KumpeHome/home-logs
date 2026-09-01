import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { timeOfDayGreeting } from '../../shared/greeting';

@Component({
  selector: 'hl-dashboard',
  imports: [DatePipe, FormsModule, RouterLink],
  template: `
    <header class="page-head">
      <div>
        <p class="eyebrow">{{ todayLabel() }}</p>
        <h1>{{ greeting() }}</h1>
        <p class="lede">Here's what needs your attention today.</p>
      </div>
      @if (auth.householdId()) {
        <a class="hl-btn" routerLink="/logs">Add a record</a>
      }
    </header>
    @if (!auth.householdId()) {
      <section class="hl-card">
        <h2>Welcome in</h2>
        <p class="lede">Start with a household name. You can invite people and add records after this.</p>
        <form class="hl-form" (ngSubmit)="createHome()">
          <label>Household name <input [(ngModel)]="homeName" name="hname" /></label>
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
        <article class="hl-card stat-card">
          <span class="stat-label">Household</span>
          <strong>{{ dash.active_members }}</strong>
          <span>People at home</span>
        </article>
        <article class="hl-card stat-card">
          <span class="stat-label">Away</span>
          <strong>{{ dash.inactive_members }}</strong>
          <span>Inactive members</span>
        </article>
        <article class="hl-card stat-card">
          <span class="stat-label">Drafts</span>
          <strong>{{ dash.drafts }}</strong>
          <span>Saved for later</span>
        </article>
        <article class="hl-card stat-card">
          <span class="stat-label">Medications</span>
          <strong>{{ dash.meds_due.length }}</strong>
          <span>Doses due today</span>
        </article>
      </div>
      <section class="hl-card">
        <h2>Medications due</h2>
        @for (med of dash.meds_due; track med.medication_id + med.scheduled_time) {
          <div class="attention-item">
            <div>
              <strong>{{ med.member_name }}</strong>
              <p class="muted">{{ med.medication_name }} {{ med.dose }}</p>
            </div>
            <span class="hl-pill pending">{{ med.scheduled_time }}</span>
          </div>
        } @empty {
          <div class="empty">
            <strong>No medications need attention right now.</strong>
            <span>Enjoy the quiet. New doses will show up here when they are due.</span>
          </div>
        }
      </section>
      <section class="hl-card">
        <div class="head">
          <h2>Recent records</h2>
          <a class="hl-btn secondary" routerLink="/forms">Browse submitted</a>
        </div>
        @if (dash.recent_logs?.length) {
          <div class="table-wrap">
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
          </div>
        } @else {
          <div class="empty">
            <strong>No recent records yet.</strong>
            <span>When you save a log, it will appear here so the day is easy to scan.</span>
          </div>
        }
      </section>
    }
  `,
  styles: `
    .stats { grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); margin-bottom: 1rem; }
    .attention-item { margin-bottom: 0.65rem; }
    .attention-item p { margin: 0.2rem 0 0; }
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

  greeting(): string {
    return timeOfDayGreeting(new Date().getHours(), this.auth.me()?.name);
  }

  todayLabel(): string {
    return new Intl.DateTimeFormat(undefined, {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    }).format(new Date());
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
