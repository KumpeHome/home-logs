import { Component, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { FormAction } from '../../shared/form-action';
import { FormStatus } from '../../shared/form-status';

type BehaviorRow = {
  id: string;
  member_id: string;
  occurred_at: string;
  location: string | null;
  antecedent: string;
  behavior: string;
  intervention: string;
  consequence: string;
  duration_minutes: number | null;
  follow_up: string | null;
  notified: string[];
  log_entry_id: string | null;
};

type BehaviorMember = {
  id: string;
  legal_name: string;
};

type BehaviorDraft = {
  member_id: string;
  occurred_at: string;
  location: string;
  antecedent: string;
  behavior: string;
  intervention: string;
  consequence: string;
  duration_minutes: number | null;
  follow_up: string;
};

@Component({
  selector: 'hl-discipline',
  imports: [DatePipe, FormsModule, RouterLink, FormStatus],
  templateUrl: './discipline.html',
  styleUrl: './discipline.scss',
})
export class DisciplinePage {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  readonly members = signal<BehaviorMember[]>([]);
  readonly rows = signal<BehaviorRow[]>([]);
  readonly adding = signal(false);
  readonly viewing = signal<BehaviorRow | null>(null);
  readonly formAction = new FormAction();
  editingId: string | null = null;
  notified = '';
  draft: BehaviorDraft = this.emptyDraft();

  constructor() {
    this.api.get<BehaviorMember[]>(`/households/${this.api.hid()}/members`).subscribe((rows) => {
      this.members.set(rows);
      if (!this.draft.member_id) {
        this.draft.member_id = rows[0]?.id ?? '';
      }
    });
    this.reload();
  }

  canAdd(): boolean {
    return this.auth.can('tab.discipline', 'add');
  }

  canEdit(): boolean {
    return this.auth.can('tab.discipline', 'edit');
  }

  reload(): void {
    this.api
      .get<BehaviorRow[]>(`/households/${this.api.hid()}/discipline`)
      .subscribe((rows) => {
        this.rows.set(rows);
        this.openFromQuery(rows);
      });
  }

  view(row: BehaviorRow): void {
    this.adding.set(false);
    this.editingId = null;
    this.viewing.set(row);
  }

  private openFromQuery(rows: BehaviorRow[]): void {
    const logId = this.route.snapshot.queryParamMap.get('edit');
    if (!logId) {
      return;
    }
    const row = rows.find((item) => item.log_entry_id === logId);
    if (!row) {
      return;
    }
    if (this.canEdit()) {
      this.startEdit(row);
      return;
    }
    this.view(row);
  }

  startAdd(): void {
    this.viewing.set(null);
    this.editingId = null;
    this.notified = '';
    this.draft = this.emptyDraft();
    this.draft.member_id = this.members()[0]?.id ?? '';
    this.adding.set(true);
  }

  startEdit(row: BehaviorRow): void {
    this.viewing.set(null);
    this.editingId = row.id;
    this.notified = (row.notified || []).join(', ');
    this.draft = {
      member_id: row.member_id,
      occurred_at: this.toLocalInput(row.occurred_at),
      location: row.location || 'Home',
      antecedent: row.antecedent,
      behavior: row.behavior,
      intervention: row.intervention,
      consequence: row.consequence,
      duration_minutes: row.duration_minutes ?? 10,
      follow_up: row.follow_up || '',
    };
    this.adding.set(true);
  }

  cancel(): void {
    this.adding.set(false);
    this.editingId = null;
    this.formAction.clear();
  }

  save(): void {
    const hid = this.api.hid();
    const body = {
      ...this.draft,
      occurred_at: new Date(this.draft.occurred_at || Date.now()).toISOString(),
      notified: this.notified
        .split(',')
        .map((item: string) => item.trim())
        .filter(Boolean),
      duration_minutes: this.parseMinutes(this.draft.duration_minutes),
    };
    const request = this.editingId
      ? this.api.patch(`/households/${hid}/discipline/${this.editingId}`, body)
      : this.api.post(`/households/${hid}/discipline`, body);
    this.formAction.run(request, this.editingId ? 'Note saved.' : 'Note added.', () => {
      this.cancel();
      this.reload();
    });
  }

  private parseMinutes(value: unknown): number | null {
    const minutes = Number(value);
    return Number.isFinite(minutes) ? minutes : null;
  }

  private emptyDraft(): BehaviorDraft {
    return {
      member_id: '',
      occurred_at: this.nowLocal(),
      location: 'Home',
      antecedent: '',
      behavior: '',
      intervention: '',
      consequence: '',
      duration_minutes: 10,
      follow_up: '',
    };
  }

  private nowLocal(): string {
    return this.toLocalInput(new Date().toISOString());
  }

  private toLocalInput(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return '';
    }
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }
}
