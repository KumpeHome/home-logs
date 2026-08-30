import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of } from 'rxjs';
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
  });
});
