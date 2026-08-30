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
    <div class="head">
      <h1>People</h1>
      <label>Show inactive <input type="checkbox" [(ngModel)]="includeInactive" (change)="load()" /></label>
    </div>
    @if (auth.can('tab.people', 'add')) {
    <section class="hl-card">
      <h2>Add member</h2>
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
        <button class="hl-btn" type="submit">Add</button>
      </form>
    </section>
    }
    <table>
      <tr><th>Name</th><th>Role</th><th>Status</th><th>Login</th><th></th></tr>
      @for (member of members(); track member.id) {
        <tr>
          <td>
            <a class="person" [routerLink]="['/people', member.id]">
              <hl-member-photo
                [householdId]="api.hid()"
                [memberId]="member.id"
                [name]="member.legal_name"
                [hasPhoto]="member.has_photo"
              />
              {{ member.legal_name }}
            </a>
          </td>
          <td>{{ member.household_role }}</td>
          <td><span class="hl-pill" [class.active]="member.status==='active'" [class.inactive]="member.status!=='active'">{{ member.status }}</span></td>
          <td><span class="hl-pill pending">{{ member.login_status }}</span></td>
          <td>
            @if (member.login_status !== 'linked' && member.email) {
              <button class="hl-btn secondary" (click)="invite(member.id)">Invite</button>
            }
            @if (member.status === 'active') {
              <button class="hl-btn secondary" (click)="deactivate(member.id)">Deactivate</button>
            } @else {
              <button class="hl-btn secondary" (click)="activate(member.id)">Activate</button>
            }
          </td>
        </tr>
      }
    </table>
  `,
})
export class PeoplePage {
  readonly api = inject(ApiService);
  readonly auth = inject(AuthService);
  readonly members = signal<any[]>([]);
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
    this.api.post(`/households/${this.api.hid()}/members`, this.draft).subscribe(() => this.load());
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
