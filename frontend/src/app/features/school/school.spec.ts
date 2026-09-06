import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { PAPER_SCAN_ENGINE_LOADER } from '../../shared/paper-scan';
import { SchoolPage } from './school';

describe('SchoolPage report cards', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SchoolPage],
      providers: [
        provideHttpClient(),
        {
          provide: ApiService,
          useValue: {
            hid: () => 'h1',
            get: (path: string) => {
              if (path.includes('/enrollments')) {
                return of([
                  {
                    id: 'e1',
                    school_name: 'Lincoln',
                    school_year: '2026-2027',
                    grade_level: '3',
                    iep: false,
                    plan_504: false,
                    grades: [],
                    report_cards: [],
                  },
                ]);
              }
              return of([{ id: 'm1', legal_name: 'Casey Child' }]);
            },
            post: () => of({}),
            upload: () => of({}),
          },
        },
        { provide: PAPER_SCAN_ENGINE_LOADER, useValue: async () => ({}) },
      ],
    }).compileComponents();
  });

  it('lets you scan a report card with the camera', async () => {
    const fixture = TestBed.createComponent(SchoolPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.querySelector('[data-test="scan-document"]')).toBeTruthy();
    expect(host.textContent).toContain('Scan with camera');
  });
});
