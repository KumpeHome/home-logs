import { Component, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';

@Component({
  selector: 'hl-documents',
  imports: [DatePipe, FormsModule],
  template: `
    <header class="page-head">
      <div>
        <p class="eyebrow">Records</p>
        <h1>Documents</h1>
        <p class="lede">Keep the important papers close without turning the home into a filing cabinet.</p>
      </div>
      @if (!adding()) {
        <button class="hl-btn" type="button" (click)="adding.set(true)">Upload document</button>
      }
    </header>
    @if (adding()) {
    <section class="hl-card">
      <div class="head">
        <h2>Upload a file</h2>
        <button class="hl-btn ghost" type="button" (click)="adding.set(false)">Cancel</button>
      </div>
      <form class="hl-form" (ngSubmit)="upload()">
        <label>Title <input [(ngModel)]="title" name="title" /></label>
        <label>Category
          <select [(ngModel)]="category" name="cat">
            <option value="court">Court</option>
            <option value="medical">Medical</option>
            <option value="school">School</option>
            <option value="insurance">Insurance</option>
            <option value="placement">Placement</option>
            <option value="other">Other</option>
          </select>
        </label>
        <label>Member
          <select [(ngModel)]="memberId" name="mid">
            <option value="">Household</option>
            @for (member of members(); track member.id) {
              <option [value]="member.id">{{ member.legal_name }}</option>
            }
          </select>
        </label>
        <label>File <input type="file" (change)="onFile($event)" /></label>
        <button class="hl-btn">Upload document</button>
      </form>
    </section>
    }
    @if (docs().length) {
      <div class="table-wrap">
        <table>
          <tr><th>Title</th><th>Category</th><th>File</th><th>When</th></tr>
          @for (doc of docs(); track doc.id) {
            <tr>
              <td>{{ doc.title }}</td>
              <td>{{ doc.category }}</td>
              <td>{{ doc.filename }}</td>
              <td>{{ doc.created_at | date:'short' }}</td>
            </tr>
          }
        </table>
      </div>
    } @else if (!adding()) {
      <section class="hl-card">
        <div class="empty">
          <strong>No documents yet</strong>
          <span>Upload medical, school, or household files so they are easy to find later.</span>
        </div>
      </section>
    }
  `,
})
export class DocumentsPage {
  private readonly api = inject(ApiService);
  readonly docs = signal<any[]>([]);
  readonly members = signal<any[]>([]);
  readonly adding = signal(false);
  title = '';
  category = 'other';
  memberId = '';
  file: File | null = null;

  constructor() {
    this.api.get<any[]>(`/households/${this.api.hid()}/members`).subscribe((rows) => this.members.set(rows));
    this.reload();
  }

  reload(): void {
    this.api.get<any[]>(`/households/${this.api.hid()}/documents`).subscribe((rows) => this.docs.set(rows));
  }

  onFile(event: Event): void {
    this.file = (event.target as HTMLInputElement).files?.[0] ?? null;
  }

  upload(): void {
    if (!this.file) return;
    const form = new FormData();
    form.append('file', this.file);
    form.append('title', this.title);
    form.append('category', this.category);
    if (this.memberId) form.append('member_id', this.memberId);
    this.api.upload(`/households/${this.api.hid()}/documents`, form).subscribe(() => {
      this.adding.set(false);
      this.reload();
    });
  }
}
