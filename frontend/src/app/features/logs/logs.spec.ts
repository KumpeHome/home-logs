import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { LogsPage } from './logs';

const apiMock = {
  hid: () => 'h1',
  timezone: () => 'America/Chicago',
  get: (path: string) => {
    if (path === '/form-types') {
      return of([
        {
          code: 'medication_administration',
          name: 'Medication administration',
          description: 'Record a dose',
          schema: {},
        },
      ]);
    }
    if (path.includes('/members/m1/profile')) {
      return of({
        medications: [
          {
            id: 'current',
            name: 'Cetirizine',
            dose: '5mg',
            active: true,
            start_date: null,
            end_date: null,
            flags: ['drowsy', 'take_with_food'],
          },
          {
            id: 'expired',
            name: 'Old Antibiotic',
            dose: '400mg',
            active: true,
            start_date: '2025-01-01',
            end_date: '2025-01-10',
            flags: [],
          },
        ],
        otc_medications: [],
      });
    }
    if (path.includes('/otc-medications')) {
      return of([{ id: 'otc1', name: 'Acetaminophen', dose: '325mg', active: true }]);
    }
    if (path.includes('/members')) {
      return of([{ id: 'm1', legal_name: 'Casey Child' }]);
    }
    return of([]);
  },
  post: () => of({}),
};

describe('LogsPage medication administration', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LogsPage],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        { provide: ApiService, useValue: apiMock },
      ],
    }).compileComponents();
  });

  it('omits meds outside start/end and shows awareness flag bubbles', async () => {
    const fixture = TestBed.createComponent(LogsPage);
    fixture.detectChanges();
    await fixture.whenStable();
    const page = fixture.componentInstance;
    page.formCode = 'medication_administration';
    page.memberId = 'm1';
    page.start();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).toContain('Cetirizine');
    expect(host.textContent).not.toContain('Old Antibiotic');
    expect(host.textContent).toContain('Acetaminophen');
    expect(host.textContent).toContain('(OTC)');
    expect(host.querySelector('[data-test="med-flags"]')?.textContent).toContain('Drowsy');
    expect(host.querySelector('[data-test="med-flags"]')?.textContent).toContain('Take with food');
  });

  it('defaults date and time to now and asks for quantity plus drawn initials', async () => {
    const fixture = TestBed.createComponent(LogsPage);
    fixture.detectChanges();
    await fixture.whenStable();
    const page = fixture.componentInstance;
    page.formCode = 'medication_administration';
    page.memberId = 'm1';
    page.start();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).not.toContain('Witness');
    expect(host.textContent).not.toContain('Dose given');
    const when = host.querySelector('[data-test="mar-occurred"]') as HTMLInputElement;
    expect(when).toBeTruthy();
    expect(when.value).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
    expect(host.querySelector('[data-test="quantity-given"]')).toBeTruthy();
    expect(host.querySelector('[data-test="fp-initials"]')).toBeTruthy();
    expect(host.querySelector('[data-test="fc-initials"]')).toBeTruthy();
    expect(host.textContent).toContain('Your initials');
    expect(host.textContent).toContain('Child initials');
  });

  it('keeps initials pads outside labels so mouseup does not click Clear', async () => {
    const fixture = TestBed.createComponent(LogsPage);
    fixture.detectChanges();
    await fixture.whenStable();
    const page = fixture.componentInstance;
    page.formCode = 'medication_administration';
    page.memberId = 'm1';
    page.start();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    for (const testId of ['fp-initials', 'fc-initials']) {
      const canvas = host.querySelector(`[data-test="${testId}"]`);
      expect(canvas).toBeTruthy();
      expect(canvas?.closest('label')).toBeNull();
    }
  });

  it('posts drawn initials when recording administration', async () => {
    const posted: unknown[] = [];
    await TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [LogsPage],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        {
          provide: ApiService,
          useValue: {
            ...apiMock,
            timezone: () => 'America/Chicago',
            post: (_path: string, body: unknown) => {
              posted.push(body);
              return of({});
            },
          },
        },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(LogsPage);
    fixture.detectChanges();
    await fixture.whenStable();
    const page = fixture.componentInstance;
    page.formCode = 'medication_administration';
    page.memberId = 'm1';
    page.start();
    fixture.detectChanges();
    await fixture.whenStable();
    page.mar.fp_initials = 'data:image/png;base64,fp';
    page.mar.fc_initials = 'data:image/png;base64,fc';
    page.saveMar();
    const body = posted[0] as { payload: { fp_initials: string; fc_initials: string } };
    expect(body.payload.fp_initials).toBe('data:image/png;base64,fp');
    expect(body.payload.fc_initials).toBe('data:image/png;base64,fc');
  });

  it('disables save while recording, then shows success and clears the form', async () => {
    const pending = new Subject<{ id: string }>();
    await TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [LogsPage],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        {
          provide: ApiService,
          useValue: {
            ...apiMock,
            timezone: () => 'America/Chicago',
            post: () => pending,
          },
        },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(LogsPage);
    fixture.detectChanges();
    await fixture.whenStable();
    const page = fixture.componentInstance;
    page.formCode = 'medication_administration';
    page.memberId = 'm1';
    page.start();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    page.mar.notes = 'With food';
    page.saveMar();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    const button = host.querySelector('[data-test="save-mar"]') as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(host.querySelector('[data-test="form-busy"]')).toBeTruthy();
    pending.next({ id: 'log-1' });
    pending.complete();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(host.querySelector('[data-test="form-success"]')?.textContent).toContain('saved');
    expect(page.mar.notes).toBe('');
  });
});

describe('LogsPage journal photos', () => {
  it('lets the user attach photos to a journal entry without putting them in the payload', async () => {
    const posted: unknown[] = [];
    const uploaded: { path: string; form: FormData }[] = [];
    await TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [LogsPage],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        {
          provide: ApiService,
          useValue: {
            hid: () => 'h1',
            timezone: () => 'America/Chicago',
            get: (path: string) => {
              if (path === '/form-types') {
                return of([
                  {
                    code: 'journal_entry',
                    name: 'Journal Entry',
                    description: 'Document bruises',
                    scope: 'member',
                    allows_photos: true,
                    schema: {
                      properties: {
                        date: { title: 'Date', format: 'date' },
                        time: { title: 'Time', format: 'time' },
                        incident: { title: 'Incident', 'x-widget': 'textarea' },
                      },
                    },
                  },
                ]);
              }
              if (path.includes('/members')) {
                return of([{ id: 'm1', legal_name: 'Casey Child', household_role: 'child' }]);
              }
              return of([]);
            },
            post: (_path: string, body: unknown) => {
              posted.push(body);
              return of({ id: 'log-9' });
            },
            upload: (path: string, form: FormData) => {
              uploaded.push({ path, form });
              return of({ id: 'att-1' });
            },
          },
        },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(LogsPage);
    fixture.detectChanges();
    await fixture.whenStable();
    const page = fixture.componentInstance;
    page.formCode = 'journal_entry';
    page.memberId = 'm1';
    page.start();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    const picker = host.querySelector('[data-test="log-photos"]') as HTMLInputElement;
    expect(picker).toBeTruthy();
    expect(picker.accept).toContain('heic');
    expect(host.textContent).toContain('not included on official reports');
    expect(host.textContent).toContain('HEIC');
    const file = new File(['png'], 'bruise.png', { type: 'image/png' });
    await page.onPhotos({ target: { files: [file] } } as unknown as Event);
    page.save({ date: '2026-08-19', time: '16:30', incident: 'Scrape' });
    await fixture.whenStable();
    const body = posted[0] as { payload: Record<string, unknown> };
    expect(body.payload).not.toHaveProperty('photos');
    expect(uploaded.length).toBe(1);
    expect(uploaded[0].path).toContain('/logs/log-9/attachments');
    const sent = uploaded[0].form.get('file') as File;
    expect(sent).toBeInstanceOf(File);
    expect(sent.name).toBe('bruise.png');
  });

  it('gives unnamed camera photos a filename so the API treats them as a file part', async () => {
    const uploaded: { path: string; form: FormData }[] = [];
    await TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [LogsPage],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        {
          provide: ApiService,
          useValue: {
            hid: () => 'h1',
            timezone: () => 'America/Chicago',
            get: (path: string) => {
              if (path === '/form-types') {
                return of([
                  {
                    code: 'incident',
                    name: 'Incident Report',
                    description: '',
                    scope: 'member',
                    allows_photos: true,
                    schema: { properties: { notes: { title: 'Notes' } } },
                  },
                ]);
              }
              if (path.includes('/members')) {
                return of([{ id: 'm1', legal_name: 'Casey Child', household_role: 'child' }]);
              }
              return of([]);
            },
            post: () => of({ id: 'log-10' }),
            upload: (path: string, form: FormData) => {
              uploaded.push({ path, form });
              return of({ id: 'att-1' });
            },
          },
        },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(LogsPage);
    fixture.detectChanges();
    await fixture.whenStable();
    const page = fixture.componentInstance;
    page.formCode = 'incident';
    page.memberId = 'm1';
    page.start();
    fixture.detectChanges();
    await fixture.whenStable();
    const unnamed = new File(['png'], '', { type: 'image/png' });
    await page.onPhotos({ target: { files: [unnamed] } } as unknown as Event);
    page.save({ notes: 'Scraped knee' });
    await fixture.whenStable();
    expect(uploaded.length).toBe(1);
    expect((uploaded[0].form.get('file') as File).name).toBe('photo.jpg');
  });

  it('blocks unsupported files before save and shows the API detail if upload fails', async () => {
    const uploaded: { path: string; form: FormData }[] = [];
    await TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [LogsPage],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        {
          provide: ApiService,
          useValue: {
            hid: () => 'h1',
            timezone: () => 'America/Chicago',
            get: (path: string) => {
              if (path === '/form-types') {
                return of([
                  {
                    code: 'incident',
                    name: 'Incident Report',
                    description: '',
                    scope: 'member',
                    allows_photos: true,
                    schema: { properties: { notes: { title: 'Notes' } } },
                  },
                ]);
              }
              if (path.includes('/members')) {
                return of([{ id: 'm1', legal_name: 'Casey Child', household_role: 'child' }]);
              }
              return of([]);
            },
            post: () => of({ id: 'log-11' }),
            upload: (path: string, form: FormData) => {
              uploaded.push({ path, form });
              return throwError(() => ({
                status: 400,
                error: {
                  detail:
                    'This HEIC photo could not be read. Save it as JPEG or PNG and try again.',
                },
              }));
            },
          },
        },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(LogsPage);
    fixture.detectChanges();
    await fixture.whenStable();
    const page = fixture.componentInstance;
    page.formCode = 'incident';
    page.memberId = 'm1';
    page.start();
    fixture.detectChanges();
    await fixture.whenStable();
    const pdf = new File(['%PDF'], 'scan.pdf', { type: 'application/pdf' });
    await page.onPhotos({ target: { files: [pdf] } } as unknown as Event);
    expect(page.saveError()).toMatch(/JPEG, PNG, GIF, WebP, or HEIC/i);
    expect(page.photos).toEqual([]);
    const png = new File(['png'], 'bruise.png', { type: 'image/png' });
    await page.onPhotos({ target: { files: [png] } } as unknown as Event);
    page.save({ notes: 'Scraped knee' });
    await fixture.whenStable();
    expect(page.saveError()).toContain('HEIC photo could not be read');
  });

  it('does not clear a pending save when Continue is clicked or photos change', async () => {
    const pending = new Subject<{ id: string }>();
    await TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [LogsPage],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        {
          provide: ApiService,
          useValue: {
            hid: () => 'h1',
            timezone: () => 'America/Chicago',
            get: (path: string) => {
              if (path === '/form-types') {
                return of([
                  {
                    code: 'incident',
                    name: 'Incident Report',
                    description: '',
                    scope: 'member',
                    allows_photos: true,
                    schema: { properties: { notes: { title: 'Notes' } } },
                  },
                ]);
              }
              if (path.includes('/members')) {
                return of([{ id: 'm1', legal_name: 'Casey Child', household_role: 'child' }]);
              }
              return of([]);
            },
            post: () => pending,
            upload: () => of({ id: 'att-1' }),
          },
        },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(LogsPage);
    fixture.detectChanges();
    await fixture.whenStable();
    const page = fixture.componentInstance;
    page.formCode = 'incident';
    page.memberId = 'm1';
    page.start();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const original = new File(['png'], 'bruise.png', { type: 'image/png' });
    await page.onPhotos({ target: { files: [original] } } as unknown as Event);
    page.save({ notes: 'Scraped knee' });
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    const continueBtn = host.querySelector('[data-test="log-continue"]') as HTMLButtonElement;
    const picker = host.querySelector('[data-test="log-photos"]') as HTMLInputElement;
    expect(page.formAction.busy()).toBe(true);
    expect(continueBtn.disabled).toBe(true);
    expect(picker.disabled).toBe(true);
    const selected = page.selected();
    const { photos } = page;
    page.formCode = 'daily_care';
    page.start();
    const other = new File(['png'], 'other.png', { type: 'image/png' });
    await page.onPhotos({ target: { files: [other] } } as unknown as Event);
    expect(page.formAction.busy()).toBe(true);
    expect(page.selected()).toBe(selected);
    expect(page.photos).toBe(photos);
    expect(page.photos[0]?.name).toBe('bruise.png');
  });
});

describe('LogsPage training certificates', () => {
  it('lets you upload or scan a certificate on a training log', async () => {
    const posted: unknown[] = [];
    const uploaded: { path: string; form: FormData }[] = [];
    await TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [LogsPage],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        {
          provide: ApiService,
          useValue: {
            hid: () => 'h1',
            timezone: () => 'America/Chicago',
            get: (path: string) => {
              if (path === '/form-types') {
                return of([
                  {
                    code: 'training',
                    name: 'Training',
                    description: 'Foster parent training',
                    scope: 'household',
                    allows_certificates: true,
                    schema: {
                      properties: {
                        date: { title: 'Date', format: 'date' },
                        topic: { title: 'Topic' },
                      },
                    },
                  },
                ]);
              }
              if (path.includes('/members')) {
                return of([]);
              }
              return of([]);
            },
            post: (_path: string, body: unknown) => {
              posted.push(body);
              return of({ id: 'log-12' });
            },
            upload: (path: string, form: FormData) => {
              uploaded.push({ path, form });
              return of({ id: 'att-cpr' });
            },
          },
        },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(LogsPage);
    fixture.detectChanges();
    await fixture.whenStable();
    const page = fixture.componentInstance;
    page.formCode = 'training';
    page.start();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.querySelector('[data-test="log-certificate"]')).toBeTruthy();
    expect(host.querySelector('[data-test="scan-document"]')).toBeTruthy();
    expect(host.textContent).toContain('Certificate');
    expect(host.textContent).toContain('Scan with camera');
    page.onCertificate(new File(['%PDF'], 'cpr.pdf', { type: 'application/pdf' }));
    page.save({ date: '2026-08-19', topic: 'CPR' });
    await fixture.whenStable();
    const body = posted[0] as { payload: Record<string, unknown> };
    expect(body.payload).not.toHaveProperty('certificate');
    expect(uploaded.length).toBe(1);
    expect(uploaded[0].path).toContain('/logs/log-12/attachments');
    expect((uploaded[0].form.get('file') as File).name).toBe('cpr.pdf');
  });
});
