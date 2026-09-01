import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { MemberPhoto } from '../../shared/member-photo';

@Component({
  selector: 'hl-people',
  imports: [FormsModule, RouterLink, MemberPhoto],
  template: `
    <header class="page-head">
      <div>
        <p class="eyebrow">Household</p>
        <h1>Members</h1>
        <p class="lede">The people this home looks after, all in one place.</p>
      </div>
      <div class="head-actions">
        <label class="inline-toggle">Show inactive <input type="checkbox" [(ngModel)]="includeInactive" (change)="load()" /></label>
        @if (auth.can('tab.people', 'add') && !adding()) {
          <button class="hl-btn" type="button" data-test="add-member" (click)="adding.set(true)">Add member</button>
        }
      </div>
    </header>
    @if (auth.can('tab.people', 'add') && adding()) {
    <section class="hl-card">
      <div class="head">
        <h2>Add member</h2>
        <button class="hl-btn ghost" type="button" (click)="adding.set(false)">Cancel</button>
      </div>
      <form class="hl-form" (ngSubmit)="add()">
        <label>First <input [(ngModel)]="draft.first_name" name="first" required /></label>
        <label>Last <input [(ngModel)]="draft.last_name" name="last" required /></label>
        <label>Role
          <select [(ngModel)]="draft.household_role" name="role">
            <option value="admin">Admin</option>
            <option value="adult">Adult</option>
            <option value="child">Child</option>
            <option value="other">Other</option>
          </select>
        </label>
        <label>Email <input [(ngModel)]="draft.email" name="email" /></label>
        <label class="inline"><input type="checkbox" [(ngModel)]="draft.invite" name="invite" /> Invite login (pending until first sign-in)</label>
        <button class="hl-btn" type="submit">Add member</button>
      </form>
    </section>
    }
    @if (members().length) {
      <div class="person-grid">
        @for (member of members(); track member.id) {
          <article class="hl-card person-card card-interactive">
            <a class="person" [routerLink]="['/people', member.id]">
              <hl-member-photo
                [householdId]="api.hid()"
                [memberId]="member.id"
                [name]="member.legal_name"
                [hasPhoto]="member.has_photo"
              />
              <div>
                <strong>{{ member.legal_name }}</strong>
                <p class="muted">{{ member.household_role }}</p>
              </div>
            </a>
            <div class="flag-row">
              <span class="hl-pill" [class.active]="member.status==='active'" [class.inactive]="member.status!=='active'">{{ member.status }}</span>
              <span class="hl-pill pending">{{ member.login_status }}</span>
            </div>
            <div class="actions">
              @if (member.login_status !== 'linked' && member.email) {
                <button class="hl-btn secondary" (click)="invite(member.id)">Invite</button>
              }
              @if (member.status === 'active') {
                <button class="hl-btn secondary" (click)="deactivate(member.id)">Deactivate</button>
              } @else {
                <button class="hl-btn secondary" (click)="activate(member.id)">Activate</button>
              }
            </div>
          </article>
        }
      </div>
    } @else {
      <section class="hl-card">
        <div class="empty">
          <strong>No household members yet</strong>
          <span>Add the people who live here so logs, medications, and school notes have a home.</span>
        </div>
      </section>
    }
  `,
  styles: `
    .head-actions { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; }
    .inline-toggle { display: flex; align-items: center; gap: 0.45rem; color: var(--kh-text-secondary); font-size: 0.9rem; }
    .person p { margin: 0.15rem 0 0; }
  `,
})
export class PeoplePage {
  readonly api = inject(ApiService);
  readonly auth = inject(AuthService);
  readonly members = signal<any[]>([]);
  readonly adding = signal(false);
  includeInactive = false;
  draft = {
    first_name: '',
    last_name: '',
    household_role: 'child',
    email: '',
    invite: false,
  };

  constructor() {
    this.load();
  }

  load(): void {
    const q = this.includeInactive ? '?include_inactive=true' : '';
    this.api.get<any[]>(`/households/${this.api.hid()}/members${q}`).subscribe((rows) => this.members.set(rows));
  }

  add(): void {
    this.api.post(`/households/${this.api.hid()}/members`, this.draft).subscribe(() => {
      this.adding.set(false);
      this.draft = { first_name: '', last_name: '', household_role: 'child', email: '', invite: false };
      this.load();
    });
  }

  invite(id: string): void {
    this.api.post(`/households/${this.api.hid()}/members/${id}/invite`, {}).subscribe(() => this.load());
  }

  deactivate(id: string): void {
    this.api.post(`/households/${this.api.hid()}/members/${id}/deactivate`, { reason: 'Left household' }).subscribe(() => this.load());
  }

  activate(id: string): void {
    this.api.post(`/households/${this.api.hid()}/members/${id}/activate`, {}).subscribe(() => this.load());
  }
}
