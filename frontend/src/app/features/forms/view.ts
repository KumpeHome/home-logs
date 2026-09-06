import { Component, inject, OnDestroy, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, forkJoin, of, firstValueFrom } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { NamedMember, SubmissionField, submissionFields } from '../../shared/log-display';

type LogAttachment = { id: string; filename: string; content_type: string };
type PhotoView = LogAttachment & { url: string };

@Component({
  selector: 'hl-form-view',
  imports: [DatePipe, RouterLink],
  templateUrl: './view.html',
  styleUrl: './view.scss',
})
export class FormViewPage implements OnDestroy {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  readonly log = signal<any>(null);
  readonly fields = signal<SubmissionField[]>([]);
  readonly photos = signal<PhotoView[]>([]);
  readonly error = signal<string | null>(null);
  readonly exporting = signal(false);

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
      this.loadPhotos(bundle.log.attachments ?? []);
    });
  }

  ngOnDestroy(): void {
    for (const photo of this.photos()) {
      URL.revokeObjectURL(photo.url);
    }
  }

  async exportEntry(includePhotos: boolean): Promise<void> {
    const entry = this.log();
    if (!entry) {
      return;
    }
    this.error.set(null);
    this.exporting.set(true);
    const query = includePhotos ? '?include_photos=true' : '';
    try {
      const blob = await firstValueFrom(
        this.api.getBlob(`/households/${this.api.hid()}/logs/${entry.id}/export${query}`),
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = includePhotos ? 'log-entry-photos.pdf' : 'log-entry.pdf';
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      this.error.set('Could not export this record. Try again.');
    } finally {
      this.exporting.set(false);
    }
  }

  private loadPhotos(attachments: LogAttachment[]): void {
    const hid = this.api.hid();
    const entry = this.log();
    if (!entry || !attachments.length) {
      this.photos.set([]);
      return;
    }
    forkJoin(
      attachments.map((item) =>
        this.api
          .getBlob(`/households/${hid}/logs/${entry.id}/attachments/${item.id}`)
          .pipe(catchError(() => of(null))),
      ),
    ).subscribe((blobs) => {
      const loaded: PhotoView[] = [];
      let failed = false;
      attachments.forEach((item, index) => {
        const blob = blobs[index];
        if (!blob) {
          failed = true;
          return;
        }
        loaded.push({ ...item, url: URL.createObjectURL(blob) });
      });
      this.photos.set(loaded);
      if (failed) {
        this.error.set('One or more photos could not be loaded.');
      }
    });
  }
}
