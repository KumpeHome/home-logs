import { Component, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';

@Component({
  selector: 'hl-documents',
  imports: [DatePipe, FormsModule],
  template: `
    <h1>Documents</h1>
    <section class="hl-card">
      <form class="hl-form" (ngSubmit)="upload()">
        <label>Title <input [(ngModel)]="title" name="title" /></label>
        <label>Category
          <select [(ngModel)]="category" name="cat">
            <option>court</option>
            <option>medical</option>
            <option>school</option>
            <option>insurance</option>
            <option>placement</option>
            <option>other</option>
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
        <button class="hl-btn">Upload</button>
      </form>
    </section>
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
  `,
})
export class DocumentsPage {
  private readonly api = inject(ApiService);
  readonly docs = signal<any[]>([]);
  readonly members = signal<any[]>([]);
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
    this.api.upload(`/households/${this.api.hid()}/documents`, form).subscribe(() => this.reload());
  }
}
