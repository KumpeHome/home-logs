import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
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
      providers: [provideHttpClient(), provideRouter([]), { provide: ApiService, useValue: apiMock }],
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
});
