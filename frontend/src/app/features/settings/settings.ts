import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { composeDose, DOSE_UNITS, parseDose } from '../../shared/dose';
import { FormAction } from '../../shared/form-action';
import { FormStatus } from '../../shared/form-status';
import { needsRefill, optionalQuantity, stockLabel } from '../../shared/medication';

@Component({
  selector: 'hl-settings',
  imports: [FormsModule, FormStatus],
  template: `
    <header class="page-head">
      <div>
        <p class="eyebrow">Account</p>
        <h1>Household settings</h1>
        <p class="lede">A few details about this home, plus the shared medicine cabinet.</p>
      </div>
    </header>
    @if (household(); as h) {
      <form class="hl-card hl-form" (ngSubmit)="save()">
        <label>Name <input [(ngModel)]="h.name" name="name" /></label>
        <label
          >Type
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
        <hl-form-status
          [busy]="householdAction.busy()"
          [success]="householdAction.success()"
          [error]="householdAction.error()"
        />
        <button class="hl-btn" [disabled]="householdAction.busy()">
          {{ householdAction.busy() ? 'Saving…' : 'Save changes' }}
        </button>
      </form>
    }
    <section class="hl-card">
      <div class="head">
        <h2>Medicine cabinet</h2>
      </div>
      <p class="muted">
        Household over-the-counter medications that can be assigned on a person’s Health tab.
      </p>
      <ul>
        @for (item of otc(); track item.id) {
          <li>
            {{ item.name }} {{ item.dose }} {{ item.route }}
            @if (stockText(item); as stock) {
              <span class="hl-pill pending">{{ stock }}</span>
            }
            @if (lowStock(item)) {
              <span class="hl-pill inactive">Needs refill</span>
            }
            <button
              class="hl-btn secondary"
              type="button"
              data-test="edit-otc"
              (click)="startEditOtc(item)"
            >
              Edit
            </button>
            @if (item.refill_quantity) {
              <button
                class="hl-btn secondary"
                type="button"
                data-test="record-otc-refill"
                [disabled]="otcAction.busy()"
                (click)="recordOtcRefill(item.id)"
              >
                Record refill
              </button>
            }
            <button class="hl-btn secondary" type="button" (click)="removeOtc(item.id)">
              Remove
            </button>
          </li>
        } @empty {
          <li class="muted">None yet.</li>
        }
      </ul>
      <form class="hl-form" (ngSubmit)="saveOtc()">
        <label>Name <input [(ngModel)]="otcDraft.name" name="otcname" /></label>
        <div class="dose-row">
          <label
            >Dose
            <input
              type="number"
              min="0"
              step="any"
              [(ngModel)]="otcDraft.dose_amount"
              name="otcdoseamt"
              data-test="otc-dose-amount"
            />
          </label>
          <label
            >Unit
            <select [(ngModel)]="otcDraft.dose_unit" name="otcdoseunit" data-test="otc-dose-unit">
              @for (unit of doseUnits; track unit) {
                <option [value]="unit">{{ unit }}</option>
              }
            </select>
          </label>
        </div>
        <label>Route <input [(ngModel)]="otcDraft.route" name="otcroute" /></label>
        <label
          >Instructions <textarea [(ngModel)]="otcDraft.instructions" name="otcins"></textarea>
        </label>
        <label
          >Pills / units on hand
          <input
            type="number"
            min="0"
            step="any"
            [(ngModel)]="otcDraft.quantity_on_hand"
            name="otcqty"
            data-test="otc-quantity-on-hand"
          />
        </label>
        <label
          >Amount per refill
          <input
            type="number"
            min="0"
            step="any"
            [(ngModel)]="otcDraft.refill_quantity"
            name="otcrefillqty"
            data-test="otc-refill-quantity"
          />
        </label>
        <label
          >Remind when at or below
          <input
            type="number"
            min="0"
            step="any"
            [(ngModel)]="otcDraft.refill_reminder_level"
            name="otcrefilllevel"
            data-test="otc-refill-level"
          />
        </label>
        <hl-form-status
          [busy]="otcAction.busy()"
          [success]="otcAction.success()"
          [error]="otcAction.error()"
        />
        <button
          class="hl-btn"
          type="submit"
          [attr.data-test]="editingOtcId() ? 'save-otc' : 'add-otc'"
          [disabled]="otcAction.busy()"
        >
          {{
            otcAction.busy() ? 'Saving…' : editingOtcId() ? 'Save changes' : 'Add OTC medication'
          }}
        </button>
        @if (editingOtcId()) {
          <button
            class="hl-btn secondary"
            type="button"
            (click)="cancelEditOtc()"
            [disabled]="otcAction.busy()"
          >
            Cancel
          </button>
        }
      </form>
    </section>
    <section class="hl-card">
      <h2>Your access</h2>
      <p class="muted">Synced from KumpeCloud Auth on each login.</p>
      <ul>
        @for (scope of auth.scopes(); track scope) {
          <li>{{ scope }}</li>
        }
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
  readonly editingOtcId = signal<string | null>(null);
  readonly householdAction = new FormAction();
  readonly otcAction = new FormAction();
  otcDraft = this.emptyOtc();

  constructor() {
    this.api.get(`/households/${this.api.hid()}`).subscribe((row) => this.household.set(row));
    this.loadOtc();
  }

  save(): void {
    this.householdAction.run(
      this.api.patch(`/households/${this.api.hid()}`, this.household()),
      'Household saved.',
      (row: unknown) => this.household.set(row),
    );
  }

  loadOtc(): void {
    this.api
      .get<any[]>(`/households/${this.api.hid()}/otc-medications`)
      .subscribe((rows) => this.otc.set(rows));
  }

  startEditOtc(item: {
    id: string;
    name: string;
    dose?: string;
    route?: string;
    instructions?: string;
    quantity_on_hand?: number | null;
    refill_quantity?: number | null;
    refill_reminder_level?: number | null;
  }): void {
    const parsed = parseDose(item.dose);
    this.editingOtcId.set(item.id);
    this.otcDraft = {
      name: item.name,
      dose_amount: parsed.amount ?? '',
      dose_unit: parsed.unit,
      route: item.route || 'oral',
      instructions: item.instructions || '',
      quantity_on_hand: item.quantity_on_hand ?? '',
      refill_quantity: item.refill_quantity ?? '',
      refill_reminder_level: item.refill_reminder_level ?? '',
    };
  }

  cancelEditOtc(): void {
    this.editingOtcId.set(null);
    this.otcDraft = this.emptyOtc();
  }

  saveOtc(): void {
    if (!this.otcDraft.name.trim() || this.otcAction.busy()) {
      return;
    }
    const body = {
      name: this.otcDraft.name,
      dose: composeDose(this.otcDraft.dose_amount, this.otcDraft.dose_unit),
      route: this.otcDraft.route,
      instructions: this.otcDraft.instructions,
      quantity_on_hand: optionalQuantity(this.otcDraft.quantity_on_hand),
      refill_quantity: optionalQuantity(this.otcDraft.refill_quantity),
      refill_reminder_level: optionalQuantity(this.otcDraft.refill_reminder_level),
    };
    const editId = this.editingOtcId();
    const request = editId
      ? this.api.patch(`/households/${this.api.hid()}/otc-medications/${editId}`, body)
      : this.api.post(`/households/${this.api.hid()}/otc-medications`, body);
    this.otcAction.run(request, editId ? 'Medication saved.' : 'Medication added.', () => {
      this.editingOtcId.set(null);
      this.otcDraft = this.emptyOtc();
      this.loadOtc();
    });
  }

  removeOtc(id: string): void {
    this.api
      .delete(`/households/${this.api.hid()}/otc-medications/${id}`)
      .subscribe(() => this.loadOtc());
  }

  recordOtcRefill(id: string): void {
    if (this.otcAction.busy()) {
      return;
    }
    this.otcAction.run(
      this.api.post(`/households/${this.api.hid()}/otc-medications/${id}/refill`, {}),
      'Refill recorded.',
      () => this.loadOtc(),
    );
  }

  stockText(item: { quantity_on_hand?: number | null }): string | null {
    return stockLabel(item);
  }

  lowStock(item: {
    quantity_on_hand?: number | null;
    refill_reminder_level?: number | null;
    needs_refill?: boolean;
  }): boolean {
    return item.needs_refill === true || needsRefill(item);
  }

  private emptyOtc() {
    return {
      name: '',
      dose_amount: '1',
      dose_unit: 'mg',
      route: 'oral',
      instructions: '',
      quantity_on_hand: '' as string | number,
      refill_quantity: '' as string | number,
      refill_reminder_level: '' as string | number,
    };
  }
}
