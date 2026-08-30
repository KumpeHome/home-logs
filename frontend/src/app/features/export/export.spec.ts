import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { ExportPage } from './export';

describe('ExportPage', () => {
  const posted: { path?: string; body?: any } = {};
  const apiMock = {
    hid: () => 'h1',
    get: (path: string) => {
      if (path === '/export-forms') {
        return of([
          {
            code: 'ar_dcfs_quarterly_drills',
            name: 'Quarterly Fire/Tornado Drills',
            category: 'Arkansas DCFS',
          },
          {
            code: 'ar_dcfs_medication_log',
            name: 'Medication Dosage Logs',
            category: 'Arkansas DCFS',
          },
          {
            code: 'ar_dcfs_sibling_contact',
            name: 'Separated Sibling Contact Report',
            category: 'Arkansas DCFS',
          },
        ]);
      }
      if (path.includes('/members')) {
        return of([
          { id: 'm1', legal_name: 'Casey Child', status: 'active', household_role: 'child' },
          { id: 'm2', legal_name: 'Sam Kid', status: 'active', household_role: 'child' },
          { id: 'a1', legal_name: 'Ada Admin', status: 'active', household_role: 'adult' },
        ]);
      }
      return of([]);
    },
    postBlob: (path: string, body: unknown) => {
      posted.path = path;
      posted.body = body;
      return of(new Blob(['%PDF'], { type: 'application/pdf' }));
    },
  };

  beforeEach(async () => {
    posted.path = undefined;
    posted.body = undefined;
    await TestBed.configureTestingModule({
      imports: [ExportPage],
      providers: [provideHttpClient(), { provide: ApiService, useValue: apiMock }],
    }).compileComponents();
  });

  it('lets the user pick a form and date range without a raw API URL', async () => {
    const fixture = TestBed.createComponent(ExportPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).toContain('Category');
    expect(host.textContent).toContain('Arkansas DCFS');
    expect(host.textContent).toContain('Form');
    expect(host.textContent).toContain('Quarterly Fire/Tornado Drills');
    expect(host.textContent).toContain('Medication Dosage Logs');
    expect(host.textContent).toContain('Separated Sibling Contact Report');
    expect(host.querySelector('[data-test="export-start"]')).toBeTruthy();
    expect(host.querySelector('[data-test="export-end"]')).toBeTruthy();
    expect(host.querySelector('[data-test="download-pdf"]')).toBeTruthy();
    expect(host.textContent).not.toContain('/api/households/');
    expect(host.textContent).not.toContain('Agency visit form');
    expect(host.querySelector('input[type="file"]')).toBeNull();
  });

  it('hides member pickers for fire/tornado drills and shows them for medication logs', async () => {
    const fixture = TestBed.createComponent(ExportPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const page = fixture.componentInstance;
    const host = fixture.nativeElement as HTMLElement;
    page.formCode.set('ar_dcfs_quarterly_drills');
    fixture.detectChanges();
    expect(host.querySelector('[data-test="export-member"]')).toBeNull();
    expect(host.textContent).not.toContain('Household members');
    page.formCode.set('ar_dcfs_medication_log');
    fixture.detectChanges();
    expect(host.querySelector('[data-test="export-member"]')).toBeTruthy();
    expect(host.textContent).toContain('Casey Child');
  });

  it('downloads the filled official form for the selected range and members', async () => {
    const fixture = TestBed.createComponent(ExportPage);
    fixture.detectChanges();
    await fixture.whenStable();
    const page = fixture.componentInstance;
    page.formCode.set('ar_dcfs_medication_log');
    page.startDate = '2026-08-01';
    page.endDate = '2026-08-31';
    page.selectedIds.add('m1');
    await page.download();
    expect(posted.path).toContain('/form-exports');
    expect(posted.body.form_code).toBe('ar_dcfs_medication_log');
    expect(posted.body.start_date).toBe('2026-08-01');
    expect(posted.body.end_date).toBe('2026-08-31');
    expect(posted.body.member_ids).toContain('m1');
  });

  it('omits member filters when downloading fire/tornado drills', async () => {
    const fixture = TestBed.createComponent(ExportPage);
    fixture.detectChanges();
    await fixture.whenStable();
    const page = fixture.componentInstance;
    page.formCode.set('ar_dcfs_quarterly_drills');
    page.startDate = '2026-08-01';
    page.endDate = '2026-08-31';
    page.selectedIds.add('m1');
    await page.download();
    expect(posted.body.form_code).toBe('ar_dcfs_quarterly_drills');
    expect(posted.body.member_ids).toEqual([]);
  });

  it('lets the user pick who the sibling contact report is for', async () => {
    const fixture = TestBed.createComponent(ExportPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const page = fixture.componentInstance;
    page.formCode.set('ar_dcfs_sibling_contact');
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.querySelector('[data-test="export-member"]')).toBeNull();
    const subject = host.querySelector('[data-test="export-subject"]') as HTMLSelectElement;
    expect(subject).toBeTruthy();
    expect(host.textContent).toContain('Exporting for');
    expect(host.textContent).toContain('Casey Child');
    expect(host.textContent).toContain('Sam Kid');
    expect(host.textContent).not.toContain('Ada Admin');
    page.exportSubject.set('m2');
    page.startDate = '2026-08-01';
    page.endDate = '2026-08-31';
    await page.download();
    expect(posted.body.form_code).toBe('ar_dcfs_sibling_contact');
    expect(posted.body.member_ids).toEqual(['m2']);
  });
});
