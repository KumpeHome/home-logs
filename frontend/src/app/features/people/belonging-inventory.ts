import { Component, inject, input, signal, type OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { ApiService } from '../../core/api.service';

type BelongingDraft = {
  item_category: string;
  description: string;
  quantity: number;
  recorded_on: string;
  initials: string;
  disposition: string;
};

type BelongingRow = {
  id: string;
  status: string;
  payload: Partial<BelongingDraft>;
};

type FormType = {
  code: string;
  schema?: { properties?: { item_category?: { enum?: string[] } } };
};

@Component({
  selector: 'hl-belonging-inventory',
  imports: [FormsModule],
  templateUrl: './belonging-inventory.html',
  styleUrl: './belonging-inventory.scss',
})
export class BelongingInventory implements OnInit {
  private readonly api = inject(ApiService);
  readonly householdId = input.required<string>();
  readonly memberId = input.required<string>();
  readonly items = signal<BelongingRow[]>([]);
  readonly categories = signal<string[]>(['Other']);
  readonly editing = signal(false);
  readonly error = signal<string | null>(null);
  draft: BelongingDraft = this.emptyDraft();
  private editingId: string | null = null;
  private editingStatus = 'submitted';

  ngOnInit(): void {
    this.reload();
  }

  reload(householdId = this.householdId(), memberId = this.memberId()): void {
    this.error.set(null);
    forkJoin({
      forms: this.api.get<FormType[]>('/form-types'),
      logs: this.api.get<BelongingRow[]>(
        `/households/${householdId}/logs?member_id=${memberId}&form_type_code=personal_belonging`,
      ),
    }).subscribe({
      next: (bundle) => {
        const form = bundle.forms.find((item) => item.code === 'personal_belonging');
        const categories = form?.schema?.properties?.item_category?.enum ?? [];
        if (categories.length) {
          this.categories.set(categories);
        }
        this.items.set(bundle.logs.filter((item) => item.status !== 'amended'));
      },
      error: () => {
        this.error.set('Could not load this inventory. Try again.');
      },
    });
  }

  startAdd(): void {
    this.editingId = null;
    this.editingStatus = 'submitted';
    this.draft = this.emptyDraft();
    this.editing.set(true);
  }

  startEdit(item: BelongingRow): void {
    this.editingId = item.id;
    this.editingStatus = item.status;
    this.draft = {
      item_category: String(item.payload.item_category || this.categories()[0] || 'Other'),
      description: String(item.payload.description || ''),
      quantity: Number(item.payload.quantity ?? 1),
      recorded_on: String(item.payload.recorded_on || ''),
      initials: String(item.payload.initials || ''),
      disposition: String(item.payload.disposition || ''),
    };
    this.editing.set(true);
  }

  cancel(): void {
    this.editing.set(false);
    this.editingId = null;
    this.draft = this.emptyDraft();
  }

  save(): void {
    this.error.set(null);
    const householdId = this.householdId();
    const memberId = this.memberId();
    const payload = {
      item_category: this.draft.item_category,
      description: this.draft.description,
      quantity: Number(this.draft.quantity) || 0,
      recorded_on: this.draft.recorded_on,
      initials: this.draft.initials,
      disposition: this.draft.disposition,
    };
    const occurredAt = this.draft.recorded_on
      ? new Date(`${this.draft.recorded_on}T12:00:00`).toISOString()
      : new Date().toISOString();
    const request = this.saveRequest(householdId, memberId, payload, occurredAt);
    request.subscribe({
      next: () => {
        this.cancel();
        this.reload(householdId, memberId);
      },
      error: (err: { error?: { detail?: unknown } }) => {
        const detail = err.error?.detail;
        this.error.set(typeof detail === 'string' ? detail : 'Could not save that item.');
      },
    });
  }

  private saveRequest(
    householdId: string,
    memberId: string,
    payload: BelongingDraft,
    occurredAt: string,
  ) {
    if (!this.editingId) {
      return this.api.post(`/households/${householdId}/logs`, {
        form_type_code: 'personal_belonging',
        subject_member_id: memberId,
        occurred_at: occurredAt,
        submit: true,
        payload,
      });
    }
    if (this.editingStatus === 'draft') {
      return this.api.patch(`/households/${householdId}/logs/${this.editingId}`, {
        form_type_code: 'personal_belonging',
        subject_member_id: memberId,
        occurred_at: occurredAt,
        payload,
      });
    }
    return this.api.post(`/households/${householdId}/logs/${this.editingId}/amend`, {
      payload,
      occurred_at: occurredAt,
      reason: 'Updated personal belonging inventory',
    });
  }

  private emptyDraft(): BelongingDraft {
    return {
      item_category: this.categories()[0] ?? 'Other',
      description: '',
      quantity: 1,
      recorded_on: new Date().toISOString().slice(0, 10),
      initials: '',
      disposition: '',
    };
  }
}
