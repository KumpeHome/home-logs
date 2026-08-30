import { Component, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, forkJoin, of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { NamedMember, SubmissionField, submissionFields } from '../../shared/log-display';

@Component({
  selector: 'hl-form-view',
  imports: [DatePipe, RouterLink],
  templateUrl: './view.html',
  styleUrl: './view.scss',
})
export class FormViewPage {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  readonly log = signal<any>(null);
  readonly fields = signal<SubmissionField[]>([]);

  timezone(): string {
    return this.api.timezone();
  }

  constructor() {
    const id = this.route.snapshot.paramMap.get('id')!;
    const hid = this.api.hid();
    forkJoin({
      log: this.api.get<any>(`/households/${hid}/logs/${id}`),
      forms: this.api.get<any[]>('/form-types'),
      members: this.api
        .get<NamedMember[]>(`/households/${hid}/members`)
        .pipe(catchError(() => of<NamedMember[]>([]))),
    }).subscribe((bundle) => {
      this.log.set(bundle.log);
      const form = bundle.forms.find((item) => item.code === bundle.log.form_type_code);
      this.fields.set(submissionFields(form?.schema, bundle.log.payload, bundle.members));
    });
  }
}
