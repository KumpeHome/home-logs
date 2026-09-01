import { Component, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { FormRenderer } from '../../shared/form-renderer';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { InitialsPad } from '../../shared/initials-pad';
import { flagLabel, isAdministerable } from '../../shared/medication';

@Component({
  selector: 'hl-logs',
  imports: [DatePipe, FormsModule, FormRenderer, InitialsPad, RouterLink],
  template: `
    <header class="page-head">
      <div>
        <p class="eyebrow">Care</p>
        <h1>Add a record</h1>
        <p class="lede">A few calm notes now make the rest of the day easier to look back on.</p>
      </div>
    </header>
    <div class="hl-card">
      <form class="hl-form" (ngSubmit)="start()">
        <label>What happened
          <select [(ngModel)]="formCode" name="form">
            @for (form of forms(); track form.code) {
              <option [value]="form.code">{{ form.name }}</option>
            }
          </select>
        </label>
        <label>Who is this for
          <select [(ngModel)]="memberId" name="member">
            <option value="">Whole household</option>
            @for (member of members(); track member.id) {
              <option [value]="member.id">{{ member.legal_name }}</option>
            }
          </select>
        </label>
        <button class="hl-btn" type="submit">Continue</button>
      </form>
    </div>
    @if (selected(); as form) {
      <section class="hl-card">
        <h2>{{ form.name }}</h2>
        <p class="muted">{{ form.description }}</p>
        @if (saveError(); as message) {
          <p class="error" data-test="save-error">{{ message }}</p>
        }
        @if (form.code === 'medication_administration') {
          <form class="hl-form" (ngSubmit)="saveMar()">
            <label>Medication
              <select [(ngModel)]="mar.medication_id" name="med">
                <option value="">Select a medication</option>
                @for (med of meds(); track med.id) {
                  <option [value]="med.id">{{ med.name }} {{ med.dose }}@if (med.is_otc) { (OTC) }</option>
                }
              </select>
            </label>
            @for (med of meds(); track med.id) {
              @if (med.id === mar.medication_id) {
                <div class="flag-row" data-test="med-flags">
                  @for (code of med.flags ?? []; track code) {
                    <span class="hl-pill pending">{{ flagName(code) }}</span>
                  }
                </div>
              }
            }
            <label>Date and time
              <input type="datetime-local" [(ngModel)]="mar.occurred_at" name="when" data-test="mar-occurred" />
            </label>
            <label>Outcome
              <select [(ngModel)]="mar.outcome" name="out">
                <option>given</option><option>refused</option><option>missed</option><option>held</option>
              </select>
            </label>
            <label>Number given
              <input type="number" min="1" step="1" [(ngModel)]="mar.quantity_given" name="qty" data-test="quantity-given" />
            </label>
            <div class="field">
              <span>Your initials</span>
              <hl-initials-pad [(value)]="mar.fp_initials" testId="fp-initials" />
            </div>
            <div class="field">
              <span>Child initials (optional)</span>
              <hl-initials-pad [(value)]="mar.fc_initials" testId="fc-initials" />
            </div>
            <label>Notes <textarea [(ngModel)]="mar.notes" name="notes"></textarea></label>
            <button class="hl-btn">Record administration</button>
          </form>
        } @else {
          <hl-form-renderer [schema]="form.schema" [members]="members()" (saved)="save($event)" />
        }
      </section>
    }
    <section class="hl-card">
      <div class="head">
        <h2>Recent history</h2>
        <a class="hl-btn secondary" routerLink="/forms">View submitted</a>
        <a class="hl-btn secondary" [href]="exportUrl('pdf')">Export PDF</a>
        <a class="hl-btn secondary" [href]="exportUrl('csv')">Export CSV</a>
      </div>
      @if (logs().length) {
        <div class="table-wrap">
          <table>
            <tr><th>When</th><th>Form</th><th>Who</th><th>Status</th><th></th></tr>
            @for (log of logs(); track log.id) {
              <tr>
                <td>{{ log.occurred_at | date:'short':timezone() }}</td>
                <td>{{ log.form_name }}</td>
                <td>{{ log.subject_name || 'Household' }}</td>
                <td><span class="hl-pill pending">{{ log.status }}</span></td>
                <td><a class="hl-btn secondary" [routerLink]="['/forms', log.id]">View</a></td>
              </tr>
            }
          </table>
        </div>
      } @else {
        <div class="empty">
          <strong>No records yet</strong>
          <span>When you save a form, it will show up here.</span>
        </div>
      }
    </section>
  `,
})
export class LogsPage {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  readonly forms = signal<any[]>([]);
  readonly members = signal<any[]>([]);
  readonly logs = signal<any[]>([]);
  readonly meds = signal<any[]>([]);
  readonly selected = signal<any>(null);
  readonly saveError = signal<string | null>(null);
  formCode = 'daily_care';
  memberId = '';
  mar: any = this.emptyMar();

  constructor() {
    this.api.get<any[]>('/form-types').subscribe((rows) => {
      const allowed = rows.filter((row) => this.auth.can(`form.${row.code}`, 'add'));
      this.forms.set(allowed);
      this.formCode = allowed[0]?.code ?? 'daily_care';
    });
    this.loadMembers();
    this.refresh();
  }

  loadMembers(): void {
    const householdId = this.api.hid();
    if (!householdId) {
      return;
    }
    this.api.get<any[]>(`/households/${householdId}/members`).subscribe((rows) => this.members.set(rows));
  }

  start(): void {
    this.saveError.set(null);
    this.loadMembers();
    const form = this.forms().find((item) => item.code === this.formCode);
    this.selected.set(form);
    if (form?.code === 'medication_administration') {
      this.mar = this.emptyMar();
    }
    if (this.memberId) {
      this.api.get<any>(`/households/${this.api.hid()}/members/${this.memberId}/profile`).subscribe((profile) => {
        const rows = [...(profile.medications ?? []), ...(profile.otc_medications ?? [])].filter(
          (item) => isAdministerable(item),
        );
        this.meds.set(rows);
        this.mar.medication_id = rows[0]?.id ?? '';
      });
    }
  }

  save(payload: Record<string, unknown>, occurredAt?: string): void {
    this.saveError.set(null);
    if (this.selected()?.scope === 'member' && !this.memberId) {
      this.saveError.set('Select a household member before saving this form.');
      return;
    }
    this.api.post(`/households/${this.api.hid()}/logs`, {
      form_type_code: this.formCode,
      subject_member_id: this.memberId || null,
      occurred_at: occurredAt ? new Date(occurredAt).toISOString() : new Date().toISOString(),
      submit: true,
      payload,
    }).subscribe({
      next: () => this.refresh(),
      error: (err: { error?: { detail?: unknown } }) => {
        const detail = err.error?.detail;
        this.saveError.set(typeof detail === 'string' ? detail : 'Could not save this form.');
      },
    });
  }

  saveMar(): void {
    const med = this.meds().find((item) => item.id === this.mar.medication_id);
    const { occurred_at: occurredAt, ...fields } = this.mar;
    this.save(
      {
        ...fields,
        medication_name: med?.name ?? '',
        quantity_given: Number(this.mar.quantity_given) || 1,
        dose_given: med?.dose ?? '',
      },
      occurredAt,
    );
  }

  private emptyMar(): Record<string, unknown> {
    return {
      medication_id: '',
      outcome: 'given',
      quantity_given: 1,
      fp_initials: '',
      fc_initials: '',
      notes: '',
      occurred_at: this.nowLocal(),
    };
  }

  private nowLocal(): string {
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
  }

  refresh(): void {
    this.api.get<any[]>(`/households/${this.api.hid()}/logs`).subscribe((rows) => this.logs.set(rows));
  }

  exportUrl(format: string): string {
    return `/api/households/${this.api.hid()}/logs-export?format=${format}`;
  }

  flagName(code: string): string {
    return flagLabel(code);
  }

  timezone(): string {
    return this.api.timezone();
  }
}
