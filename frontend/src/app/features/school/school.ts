import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';

@Component({
  selector: 'hl-school',
  imports: [FormsModule],
  template: `
    <header class="page-head">
      <div>
        <p class="eyebrow">Care</p>
        <h1>School</h1>
        <p class="lede">Enrollments, grades, and report cards without the paperwork scramble.</p>
      </div>
    </header>
    <section class="hl-card">
      <h2>New enrollment</h2>
      <form class="hl-form" (ngSubmit)="enroll()">
        <label>Member
          <select [(ngModel)]="draft.member_id" name="mid">
            @for (member of members(); track member.id) {
              <option [value]="member.id">{{ member.legal_name }}</option>
            }
          </select>
        </label>
        <label>School <input [(ngModel)]="draft.school_name" name="school" /></label>
        <label>Grade <input [(ngModel)]="draft.grade_level" name="grade" /></label>
        <label>Year <input [(ngModel)]="draft.school_year" name="year" /></label>
        <label class="inline"><input type="checkbox" [(ngModel)]="draft.iep" name="iep" /> IEP</label>
        <label class="inline"><input type="checkbox" [(ngModel)]="draft.plan_504" name="p504" /> 504</label>
        <button class="hl-btn">Save enrollment</button>
      </form>
    </section>
    @for (row of enrollments(); track row.id) {
      <section class="hl-card">
        <h2>{{ row.school_name }} — {{ row.school_year }} (grade {{ row.grade_level }})</h2>
        <p class="muted">IEP {{ row.iep ? 'yes' : 'no' }} · 504 {{ row.plan_504 ? 'yes' : 'no' }}</p>
        <table>
          <tr><th>Term</th><th>Course</th><th>Letter</th><th>%</th></tr>
          @for (grade of row.grades; track grade.id) {
            <tr><td>{{ grade.term }}</td><td>{{ grade.course }}</td><td>{{ grade.letter }}</td><td>{{ grade.percent }}</td></tr>
          }
        </table>
        <form class="hl-form" (ngSubmit)="addGrade(row.id)">
          <label>Term <input [(ngModel)]="grade.term" name="term{{row.id}}" /></label>
          <label>Course <input [(ngModel)]="grade.course" name="course{{row.id}}" /></label>
          <label>Letter <input [(ngModel)]="grade.letter" name="letter{{row.id}}" /></label>
          <label>Percent <input [(ngModel)]="grade.percent" name="pct{{row.id}}" /></label>
          <button class="hl-btn">Add grade</button>
        </form>
        <form class="hl-form" (ngSubmit)="uploadCard(row.id)">
          <label>Report card term <input [(ngModel)]="cardTerm" name="ct{{row.id}}" /></label>
          <label>File <input type="file" (change)="onFile($event)" /></label>
          <button class="hl-btn">Upload report card</button>
        </form>
        <ul>
          @for (card of row.report_cards; track card.id) {
            <li>{{ card.term }} — {{ card.filename }}</li>
          }
        </ul>
      </section>
    } @empty {
      <section class="hl-card">
        <div class="empty">
          <strong>No school enrollments yet</strong>
          <span>Add a school year when you're ready. Grades and report cards can follow.</span>
        </div>
      </section>
    }
  `,
})
export class SchoolPage {
  private readonly api = inject(ApiService);
  readonly members = signal<any[]>([]);
  readonly enrollments = signal<any[]>([]);
  draft: any = { member_id: '', school_name: '', grade_level: '', school_year: '2026-2027', iep: false, plan_504: false };
  grade: any = { term: 'Q1', course: '', letter: '', percent: '' };
  cardTerm = 'Q1';
  file: File | null = null;

  constructor() {
    this.api.get<any[]>(`/households/${this.api.hid()}/members`).subscribe((rows) => {
      this.members.set(rows);
      this.draft.member_id = rows[0]?.id ?? '';
    });
    this.reload();
  }

  reload(): void {
    this.api.get<any[]>(`/households/${this.api.hid()}/enrollments`).subscribe((rows) => this.enrollments.set(rows));
  }

  enroll(): void {
    this.api.post(`/households/${this.api.hid()}/enrollments`, this.draft).subscribe(() => this.reload());
  }

  addGrade(enrollmentId: string): void {
    this.api.post(`/households/${this.api.hid()}/enrollments/${enrollmentId}/grades`, this.grade).subscribe(() => this.reload());
  }

  onFile(event: Event): void {
    this.file = (event.target as HTMLInputElement).files?.[0] ?? null;
  }

  uploadCard(enrollmentId: string): void {
    if (!this.file) return;
    const form = new FormData();
    form.append('file', this.file);
    form.append('term', this.cardTerm);
    this.api.upload(`/households/${this.api.hid()}/enrollments/${enrollmentId}/report-cards`, form).subscribe(() => this.reload());
  }
}
