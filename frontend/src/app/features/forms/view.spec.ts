import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { FormViewPage } from './view';

const apiMock = {
  hid: () => 'h1',
  timezone: () => 'America/Chicago',
  get: (path: string) => {
    if (path === '/form-types') {
      return of([
        {
          code: 'fire_drill',
          name: 'Fire Drill',
          schema: {
            properties: {
              date: { title: 'Date' },
              meeting_point: { title: 'Meeting point' },
              evacuation_seconds: { title: 'Seconds to evacuate' },
            },
          },
        },
      ]);
    }
    if (path.endsWith('/logs/log-1')) {
      return of({
        id: 'log-1',
        form_type_code: 'fire_drill',
        form_name: 'Fire Drill',
        occurred_at: '2026-08-19T15:04:00',
        status: 'submitted',
        subject_name: null,
        payload: {
          date: '2026-08-19',
          meeting_point: 'Front oak',
          evacuation_seconds: 47,
        },
      });
    }
    if (path.includes('/members')) {
      return of([]);
    }
    return of([]);
  },
};

describe('FormViewPage', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FormViewPage],
      providers: [
        provideHttpClient(),
        provideRouter([{ path: 'forms/:id', component: FormViewPage }]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: 'log-1' }) } },
        },
        { provide: ApiService, useValue: apiMock },
      ],
    }).compileComponents();
  });

  it('shows the submitted fire drill answers', async () => {
    const fixture = TestBed.createComponent(FormViewPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Fire Drill');
    expect(text).toContain('Date');
    expect(text).toContain('2026-08-19');
    expect(text).toContain('Meeting point');
    expect(text).toContain('Front oak');
    expect(text).toContain('Seconds to evacuate');
    expect(text).toContain('47');
    expect(fixture.nativeElement.querySelector('[data-test="export-entry"]')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('[data-test="export-entry-photos"]')).toBeNull();
  });

  it('shows photos and lets the user export the entry with or without them', async () => {
    const blobs: string[] = [];
    await TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [FormViewPage],
      providers: [
        provideHttpClient(),
        provideRouter([{ path: 'forms/:id', component: FormViewPage }]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: 'log-2' }) } },
        },
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
                    schema: {
                      properties: {
                        date: { title: 'Date' },
                        incident: { title: 'Incident' },
                      },
                    },
                  },
                ]);
              }
              if (path.endsWith('/logs/log-2')) {
                return of({
                  id: 'log-2',
                  form_type_code: 'journal_entry',
                  form_name: 'Journal Entry',
                  occurred_at: '2026-08-19T21:30:00',
                  status: 'submitted',
                  subject_name: 'Casey Child',
                  payload: { date: '2026-08-19', incident: 'Small scrape' },
                  attachments: [{ id: 'att-1', filename: 'bruise.png', content_type: 'image/png' }],
                });
              }
              if (path.includes('/members')) {
                return of([]);
              }
              return of([]);
            },
            getBlob: (path: string) => {
              blobs.push(path);
              return of(new Blob(['fake'], { type: 'image/png' }));
            },
          },
        },
      ],
    }).compileComponents();
    URL.createObjectURL = () => 'blob:fake-photo';
    const fixture = TestBed.createComponent(FormViewPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).toContain('Photos');
    expect(host.querySelector('img[alt="bruise.png"]')).toBeTruthy();
    expect(host.querySelector('[data-test="export-entry"]')).toBeTruthy();
    expect(host.querySelector('[data-test="export-entry-photos"]')).toBeTruthy();
    expect(blobs.some((path) => path.includes('/attachments/att-1'))).toBe(true);
  });

  it('explains when a stored photo cannot be loaded', async () => {
    await TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [FormViewPage],
      providers: [
        provideHttpClient(),
        provideRouter([{ path: 'forms/:id', component: FormViewPage }]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: 'log-3' }) } },
        },
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
                    schema: { properties: { incident: { title: 'Incident' } } },
                  },
                ]);
              }
              if (path.endsWith('/logs/log-3')) {
                return of({
                  id: 'log-3',
                  form_type_code: 'journal_entry',
                  form_name: 'Journal Entry',
                  occurred_at: '2026-08-19T21:30:00',
                  status: 'submitted',
                  subject_name: 'Casey Child',
                  payload: { incident: 'Small scrape' },
                  attachments: [
                    { id: 'att-ok', filename: 'ok.png', content_type: 'image/png' },
                    { id: 'att-missing', filename: 'gone.png', content_type: 'image/png' },
                  ],
                });
              }
              if (path.includes('/members')) {
                return of([]);
              }
              return of([]);
            },
            getBlob: (path: string) => {
              if (path.includes('att-missing')) {
                return throwError(() => ({ status: 404, error: { detail: 'Photo not found' } }));
              }
              return of(new Blob(['fake'], { type: 'image/png' }));
            },
          },
        },
      ],
    }).compileComponents();
    URL.createObjectURL = () => 'blob:ok-photo';
    const fixture = TestBed.createComponent(FormViewPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const page = fixture.componentInstance;
    expect(page.error()).toContain('attachments could not be loaded');
    expect(page.photos().length).toBe(1);
    expect(page.photos()[0].filename).toBe('ok.png');
    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).toContain('attachments could not be loaded');
    expect(host.querySelector('img[alt="ok.png"]')).toBeTruthy();
  });

  it('shows a training certificate as a download instead of a photo', async () => {
    const blobs: string[] = [];
    await TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [FormViewPage],
      providers: [
        provideHttpClient(),
        provideRouter([{ path: 'forms/:id', component: FormViewPage }]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: 'log-4' }) } },
        },
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
                    schema: { properties: { topic: { title: 'Topic' } } },
                  },
                ]);
              }
              if (path.endsWith('/logs/log-4')) {
                return of({
                  id: 'log-4',
                  form_type_code: 'training',
                  form_name: 'Training',
                  occurred_at: '2026-08-19T18:00:00',
                  status: 'submitted',
                  subject_name: null,
                  payload: { topic: 'CPR' },
                  attachments: [
                    { id: 'att-cpr', filename: 'cpr.pdf', content_type: 'application/pdf' },
                  ],
                });
              }
              if (path.includes('/members')) {
                return of([]);
              }
              return of([]);
            },
            getBlob: (path: string) => {
              blobs.push(path);
              return of(new Blob(['%PDF'], { type: 'application/pdf' }));
            },
          },
        },
      ],
    }).compileComponents();
    URL.createObjectURL = () => 'blob:fake-cert';
    const fixture = TestBed.createComponent(FormViewPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).toContain('Certificate');
    expect(host.querySelector('img[alt="cpr.pdf"]')).toBeNull();
    const link = host.querySelector('a[download="cpr.pdf"]') as HTMLAnchorElement;
    expect(link).toBeTruthy();
    expect(link.textContent).toContain('cpr.pdf');
    expect(blobs.some((path) => path.includes('/attachments/att-cpr'))).toBe(true);
  });

  it('explains when a stored certificate cannot be loaded', async () => {
    await TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [FormViewPage],
      providers: [
        provideHttpClient(),
        provideRouter([{ path: 'forms/:id', component: FormViewPage }]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: 'log-5' }) } },
        },
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
                    schema: { properties: { topic: { title: 'Topic' } } },
                  },
                ]);
              }
              if (path.endsWith('/logs/log-5')) {
                return of({
                  id: 'log-5',
                  form_type_code: 'training',
                  form_name: 'Training',
                  occurred_at: '2026-08-19T18:00:00',
                  status: 'submitted',
                  subject_name: null,
                  payload: { topic: 'CPR' },
                  attachments: [
                    { id: 'att-cpr', filename: 'cpr.pdf', content_type: 'application/pdf' },
                  ],
                });
              }
              if (path.includes('/members')) {
                return of([]);
              }
              return of([]);
            },
            getBlob: () =>
              throwError(() => ({ status: 404, error: { detail: 'Photo not found' } })),
          },
        },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(FormViewPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fixture.componentInstance.error()).toContain('attachments could not be loaded');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain(
      'attachments could not be loaded',
    );
  });
});
