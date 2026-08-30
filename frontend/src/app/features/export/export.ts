import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';

type ExportForm = { code: string; name: string; category: string; source_forms?: string[] };
type ExportMember = { id: string; legal_name: string; household_role?: string };

@Component({
  selector: 'hl-export',
  imports: [FormsModule],
  template: `
    <h1>Export forms</h1>
    <section class="hl-card">
      <p class="muted">{{ helpText() }}</p>
      @if (error()) {
        <p class="error">{{ error() }}</p>
      }
      <form class="hl-form" (submit)="$event.preventDefault()">
        <label>Category
          <select
            data-test="export-category"
            [ngModel]="category()"
            (ngModelChange)="selectCategory($event)"
            name="category"
          >
            @for (item of categories(); track item) {
              <option [value]="item">{{ item }}</option>
            }
          </select>
        </label>
        <label>Form
          <select
            data-test="export-form"
            [ngModel]="formCode()"
            (ngModelChange)="formCode.set($event)"
            name="form"
          >
            @for (form of formsInCategory(); track form.code) {
              <option [value]="form.code">{{ form.name }}</option>
            }
          </select>
        </label>
        <label>From
          <input data-test="export-start" type="date" [(ngModel)]="startDate" name="start" />
        </label>
        <label>To
          <input data-test="export-end" type="date" [(ngModel)]="endDate" name="end" />
        </label>
        @if (needsMemberCheckboxes()) {
          <fieldset>
            <legend>Household members</legend>
            @for (member of members(); track member.id) {
              <label class="inline">
                <input
                  type="checkbox"
                  data-test="export-member"
                  [checked]="selectedIds.has(member.id)"
                  (change)="toggleMember(member.id, $event)"
                />
                {{ member.legal_name }}
              </label>
            }
          </fieldset>
        }
        @if (needsExportSubject()) {
          <label>Exporting for
            <select
              data-test="export-subject"
              [ngModel]="exportSubject()"
              (ngModelChange)="exportSubject.set($event)"
              name="subject"
            >
              @for (member of children(); track member.id) {
                <option [value]="member.id">{{ member.legal_name }}</option>
              }
            </select>
          </label>
        }
        <button class="hl-btn" type="button" data-test="download-pdf" [disabled]="downloading()" (click)="download()">
          {{ downloading() ? 'Preparing…' : 'Download PDF' }}
        </button>
      </form>
    </section>
  `,
  styles: `
    fieldset { border: 1px solid var(--hl-line); border-radius: 12px; padding: 0.75rem 1rem; }
    fieldset legend { padding: 0 0.35rem; }
    fieldset .inline { display: block; margin: 0.35rem 0; }
  `,
})
export class ExportPage {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  readonly forms = signal<ExportForm[]>([]);
  readonly members = signal<ExportMember[]>([]);
  readonly error = signal<string | null>(null);
  readonly downloading = signal(false);
  readonly category = signal('');
  readonly formCode = signal('');
  readonly exportSubject = signal('');
  startDate = '';
  endDate = '';
  selectedIds = new Set<string>();

  constructor() {
    const today = new Date();
    this.endDate = today.toISOString().slice(0, 10);
    this.startDate = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10);
    this.api.get<ExportForm[]>('/export-forms').subscribe((rows) => {
      const allowed = rows.filter((row) => this.canExport(row));
      this.forms.set(allowed);
      this.category.set(allowed[0]?.category ?? '');
      this.formCode.set(this.formsInCategory()[0]?.code ?? '');
    });
    const hid = this.api.hid();
    if (hid) {
      this.api.get<ExportMember[]>(`/households/${hid}/members`).subscribe((rows) => {
        this.members.set(rows);
        this.selectedIds = new Set(rows.map((row) => row.id));
        this.exportSubject.set(this.children()[0]?.id ?? '');
      });
    }
  }

  categories(): string[] {
    return [...new Set(this.forms().map((form) => form.category).filter(Boolean))];
  }

  formsInCategory(): ExportForm[] {
    return this.forms().filter((form) => form.category === this.category());
  }

  private canExport(form: ExportForm): boolean {
    const sources = form.source_forms ?? [];
    if (!sources.length) {
      return this.auth.can('tab.export', 'view');
    }
    return sources.some((code) => this.auth.can(`form.${code}`, 'export'));
  }

  children(): ExportMember[] {
    return this.members().filter((member) => member.household_role === 'child');
  }

  selectCategory(value: string): void {
    this.category.set(value);
    this.formCode.set(this.formsInCategory()[0]?.code ?? '');
  }

  needsMemberCheckboxes(): boolean {
    return this.formCode() === 'ar_dcfs_medication_log';
  }

  needsExportSubject(): boolean {
    return this.formCode() === 'ar_dcfs_sibling_contact';
  }

  needsMembers(): boolean {
    return this.needsMemberCheckboxes();
  }

  helpText(): string {
    if (this.formCode() === 'ar_dcfs_quarterly_drills') {
      return 'Choose a date range. Every submitted drill in that range is included, with all participants.';
    }
    if (this.formCode() === 'ar_dcfs_sibling_contact') {
      return (
        'Choose a child and a date range. Contacts that include that child are ' +
        'filled on the official CFS-400, including Foster Home Name and Provider ID ' +
        'from household name and license number.'
      );
    }
    return 'Choose a date range and who to include. Home Logs fills the PDF from submitted records.';
  }

  toggleMember(id: string, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    if (checked) {
      this.selectedIds.add(id);
    } else {
      this.selectedIds.delete(id);
    }
  }

  async download(): Promise<void> {
    if (!this.formCode()) {
      this.error.set('Choose a form to export.');
      return;
    }
    if (!this.startDate || !this.endDate) {
      this.error.set('Choose a start and end date.');
      return;
    }
    this.error.set(null);
    this.downloading.set(true);
    try {
      const blob = await firstValueFrom(
        this.api.postBlob(`/households/${this.api.hid()}/form-exports`, {
          form_code: this.formCode(),
          start_date: this.startDate,
          end_date: this.endDate,
          member_ids: this.memberIds(),
        }),
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'form-export.pdf';
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      this.error.set('Could not export that form. Try again.');
    } finally {
      this.downloading.set(false);
    }
  }

  private memberIds(): string[] {
    if (this.needsMemberCheckboxes()) {
      return [...this.selectedIds];
    }
    if (this.needsExportSubject() && this.exportSubject()) {
      return [this.exportSubject()];
    }
    return [];
  }
}
