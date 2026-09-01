import { Component, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ARRAY_WIDGETS, FieldSpec, resolveFormWidget } from './form-widget';

export interface FormMember {
  id: string;
  legal_name: string;
  household_role?: string;
}

@Component({
  selector: 'hl-form-renderer',
  imports: [FormsModule],
  template: `
    <div class="hl-form">
      @for (field of fields(); track field.key) {
        <label>
          {{ field.title }}
          @switch (field.widget) {
            @case ('textarea') {
              <textarea rows="3" [(ngModel)]="model[field.key]" [name]="field.key"></textarea>
            }
            @case ('boolean') {
              <input type="checkbox" [(ngModel)]="model[field.key]" [name]="field.key" />
            }
            @case ('select') {
              <select [(ngModel)]="model[field.key]" [name]="field.key">
                @for (option of field.options; track option) {
                  <option [value]="option">{{ option }}</option>
                }
              </select>
            }
            @case ('comma-list') {
              <input type="text" [(ngModel)]="model[field.key]" [name]="field.key" />
              <span class="muted">Separate items with commas</span>
            }
            @case ('member-checkboxes') {
              <div class="member-checks">
                @for (member of members(); track member.id) {
                  <label class="inline">
                    <input
                      type="checkbox"
                      [ngModel]="isSelected(field.key, member.id)"
                      (ngModelChange)="setSelected(field.key, member.id, $event)"
                      [name]="field.key + '-' + member.id"
                    />
                    {{ member.legal_name }}
                  </label>
                }
              </div>
            }
            @case ('member-multiselect') {
              <select
                multiple
                [(ngModel)]="model[field.key]"
                [name]="field.key"
                class="member-multiselect"
              >
                @for (member of members(); track member.id) {
                  <option [value]="member.id">{{ member.legal_name }}</option>
                }
              </select>
              <span class="muted">Select one or more household members. Hold Ctrl or Cmd to choose multiple.</span>
            }
            @case ('child-multiselect') {
              <select
                multiple
                [(ngModel)]="model[field.key]"
                [name]="field.key"
                class="child-multiselect"
              >
                @for (child of children(); track child.id) {
                  <option [value]="child.id">{{ child.legal_name }}</option>
                }
              </select>
              <span class="muted">Select one or more children. Hold Ctrl or Cmd to choose multiple.</span>
            }
            @default {
              <input [type]="field.widget" [(ngModel)]="model[field.key]" [name]="field.key" />
            }
          }
        </label>
      }
      <button class="hl-btn" type="button" (click)="emitSave()">Save record</button>
    </div>
  `,
})
export class FormRenderer {
  readonly schema = input.required<Record<string, unknown>>();
  readonly members = input<FormMember[]>([]);
  readonly saved = output<Record<string, unknown>>();
  model: Record<string, unknown> = {};

  fields(): {
    key: string;
    title: string;
    widget: string;
    type?: string;
    options?: string[];
  }[] {
    const schema = this.schema() as { properties?: Record<string, FieldSpec> };
    return Object.entries(schema.properties ?? {}).map(([key, spec]) => {
      const widget = resolveFormWidget(key, spec);
      if (ARRAY_WIDGETS.has(widget) && !Array.isArray(this.model[key])) {
        this.model[key] = [];
      }
      if (widget === 'boolean' && this.model[key] === undefined) {
        this.model[key] = false;
      }
      if (widget === 'select' && this.model[key] === undefined && spec.enum?.length) {
        this.model[key] = spec.enum[0];
      }
      return { key, title: spec.title ?? key, widget, type: spec.type, options: spec.enum };
    });
  }

  children(): FormMember[] {
    return this.members().filter((member) => member.household_role === 'child');
  }

  isSelected(key: string, memberId: string): boolean {
    return this.selectedIds(key).includes(memberId);
  }

  setSelected(key: string, memberId: string, checked: boolean): void {
    const current = this.selectedIds(key);
    if (checked && !current.includes(memberId)) {
      this.model[key] = [...current, memberId];
      return;
    }
    if (!checked) {
      this.model[key] = current.filter((id) => id !== memberId);
    }
  }

  emitSave(): void {
    const payload: Record<string, unknown> = {};
    for (const field of this.fields()) {
      const value = this.coercedValue(field);
      if (value !== undefined) {
        payload[field.key] = value;
      }
    }
    this.saved.emit(payload);
  }

  private coercedValue(field: {
    key: string;
    widget: string;
    type?: string;
  }): unknown {
    const value = this.model[field.key];
    if (field.widget === 'number' || field.type === 'integer') {
      if (value === '' || value === null || value === undefined) {
        return undefined;
      }
      const parsed = Number(value);
      return Number.isFinite(parsed) ? Math.trunc(parsed) : value;
    }
    if (field.widget === 'boolean') {
      return value === true;
    }
    if (field.widget === 'comma-list') {
      if (Array.isArray(value)) {
        return value;
      }
      if (typeof value === 'string') {
        return value.split(',').map((item) => item.trim()).filter(Boolean);
      }
      return [];
    }
    if (ARRAY_WIDGETS.has(field.widget)) {
      return Array.isArray(value) ? value : [];
    }
    return value;
  }

  private selectedIds(key: string): string[] {
    const value = this.model[key];
    return Array.isArray(value) ? value : [];
  }
}
