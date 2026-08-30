import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter, Router } from '@angular/router';
import { of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { FormsArchivePage } from './archive';

const FORM_TYPES = [
  {
    code: 'fire_drill',
    name: 'Fire Drill',
    category: 'household',
    schema: {
      properties: {
        date: { title: 'Date' },
        evacuation_seconds: { title: 'Seconds to evacuate' },
      },
    },
  },
  {
    code: 'daily_care',
    name: 'Daily Care Log',
    category: 'caregiving',
    schema: { properties: { mood: { title: 'Mood / behavior' } } },
  },
];

const apiMock = {
  hid: () => 'h1',
  timezone: () => 'America/Chicago',
  get: (path: string) => {
    if (path === '/form-types') {
      return of(FORM_TYPES);
    }
    if (path.includes('/members')) {
      return of([{ id: 'm1', legal_name: 'Casey Child' }]);
    }
    if (path.includes('/logs?form_type_code=daily_care')) {
      return of([]);
    }
    if (path.includes('/logs')) {
      return of([
        {
          id: 'log-1',
          form_type_code: 'fire_drill',
          form_name: 'Fire Drill',
          occurred_at: '2026-08-19T15:00:00',
          status: 'submitted',
          subject_name: null,
          payload: { date: '2026-08-19', evacuation_seconds: 47 },
        },
      ]);
    }
    return of([]);
  },
};

describe('FormsArchivePage', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FormsArchivePage],
      providers: [
        provideHttpClient(),
        provideRouter([
          { path: 'forms', component: FormsArchivePage },
          { path: 'forms/:id', component: FormsArchivePage },
        ]),
        { provide: ApiService, useValue: apiMock },
      ],
    }).compileComponents();
    await TestBed.inject(Router).navigateByUrl('/forms');
  });

  it('shows a tab per form type and lists submitted records with a view link', async () => {
    const fixture = TestBed.createComponent(FormsArchivePage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).toContain('Fire Drill');
    expect(host.textContent).toContain('Daily Care Log');
    expect(host.textContent).toContain('submitted');
    const view = host.querySelector('[data-test="view-form"]') as HTMLAnchorElement;
    expect(view).toBeTruthy();
    expect(view.getAttribute('href')).toContain('/forms/log-1');
  });
});
