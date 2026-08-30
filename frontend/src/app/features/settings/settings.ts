import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { composeDose, DOSE_UNITS } from '../../shared/dose';

@Component({
  selector: 'hl-settings',
  imports: [FormsModule],
  template: `
    <h1>Household settings</h1>
    @if (household(); as h) {
      <form class="hl-card hl-form" (ngSubmit)="save()">
        <label>Name <input [(ngModel)]="h.name" name="name" /></label>
        <label>Type
          <select [(ngModel)]="h.household_type" name="type">
            <option value="family">Family</option>
            <option value="foster">Foster</option>
            <option value="mixed">Mixed</option>
          </select>
        </label>
        <label>Timezone <input [(ngModel)]="h.timezone" name="tz" /></label>
        <label>Phone <input [(ngModel)]="h.phone" name="phone" /></label>
        <label>Address <input [(ngModel)]="h.address_line1" name="a1" /></label>
        <label>City <input [(ngModel)]="h.city" name="city" /></label>
        <label>Region <input [(ngModel)]="h.region" name="region" /></label>
        <label>Postal code <input [(ngModel)]="h.postal_code" name="zip" /></label>
        @if (h.household_type !== 'family') {
          <label>Agency <input [(ngModel)]="h.agency_name" name="agency" /></label>
          <label>Licensing worker <input [(ngModel)]="h.licensing_worker" name="lw" /></label>
          <label>License # / Provider ID <input [(ngModel)]="h.license_number" name="lic" /></label>
          <label>Capacity <input type="number" [(ngModel)]="h.capacity" name="cap" /></label>
        }
        <button class="hl-btn">Save</button>
      </form>
    }
    <section class="hl-card">
      <div class="head">
        <h2>Medicine cabinet</h2>
      </div>
      <p class="muted">Household over-the-counter medications that can be assigned on a person’s Health tab.</p>
      <ul>
        @for (item of otc(); track item.id) {
          <li>{{ item.name }} {{ item.dose }} {{ item.route }}
            <button class="hl-btn secondary" type="button" (click)="removeOtc(item.id)">Remove</button>
          </li>
        } @empty { <li class="muted">None yet.</li> }
      </ul>
      <form class="hl-form" (ngSubmit)="addOtc()">
        <label>Name <input [(ngModel)]="otcDraft.name" name="otcname" /></label>
        <div class="dose-row">
          <label>Dose
            <input type="number" min="0" step="any" [(ngModel)]="otcDraft.dose_amount" name="otcdoseamt" data-test="otc-dose-amount" />
          </label>
          <label>Unit
            <select [(ngModel)]="otcDraft.dose_unit" name="otcdoseunit" data-test="otc-dose-unit">
              @for (unit of doseUnits; track unit) {
                <option [value]="unit">{{ unit }}</option>
              }
            </select>
          </label>
        </div>
        <label>Route <input [(ngModel)]="otcDraft.route" name="otcroute" /></label>
        <label>Instructions <textarea [(ngModel)]="otcDraft.instructions" name="otcins"></textarea></label>
        <button class="hl-btn" type="submit" data-test="add-otc">Add OTC medication</button>
      </form>
    </section>
    <section class="hl-card">
      <h2>Your HomeLogs scopes</h2>
      <p class="muted">Synced from KumpeCloud Auth on each login. Prefix <code>homelogs:</code></p>
      <ul>
        @for (scope of auth.scopes(); track scope) { <li>{{ scope }}</li> }
      </ul>
    </section>
  `,
})
export class SettingsPage {
  private readonly api = inject(ApiService);
  readonly auth = inject(AuthService);
  readonly household = signal<any>(null);
  readonly otc = signal<any[]>([]);
  readonly doseUnits = DOSE_UNITS;
  otcDraft = { name: '', dose_amount: '1', dose_unit: 'mg', route: 'oral', instructions: '' };

  constructor() {
    this.api.get(`/households/${this.api.hid()}`).subscribe((row) => this.household.set(row));
    this.loadOtc();
  }

  save(): void {
    this.api.patch(`/households/${this.api.hid()}`, this.household()).subscribe((row: unknown) => this.household.set(row));
  }

  loadOtc(): void {
    this.api.get<any[]>(`/households/${this.api.hid()}/otc-medications`).subscribe((rows) => this.otc.set(rows));
  }

  addOtc(): void {
    if (!this.otcDraft.name.trim()) {
      return;
    }
    this.api.post(`/households/${this.api.hid()}/otc-medications`, {
      name: this.otcDraft.name,
      dose: composeDose(this.otcDraft.dose_amount, this.otcDraft.dose_unit),
      route: this.otcDraft.route,
      instructions: this.otcDraft.instructions,
    }).subscribe(() => {
      this.otcDraft = { name: '', dose_amount: '1', dose_unit: 'mg', route: 'oral', instructions: '' };
      this.loadOtc();
    });
  }

  removeOtc(id: string): void {
    this.api.delete(`/households/${this.api.hid()}/otc-medications/${id}`).subscribe(() => this.loadOtc());
  }
}
