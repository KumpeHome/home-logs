import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { DisciplinePage } from './discipline';

const NOTE = {
  id: 'd1',
  member_id: 'm1',
  occurred_at: '2026-08-19T15:04:00',
  location: 'Kitchen',
  antecedent: 'Asked to do homework',
  behavior: 'Threw pencil',
  intervention: 'Cool-down in room',
  consequence: 'Lost screen time',
  duration_minutes: 15,
  follow_up: 'Talk after dinner',
  notified: ['Case worker'],
  log_entry_id: 'log-1',
};

describe('DisciplinePage', () => {
  let patched: { path: string; body: unknown } | null;

  beforeEach(async () => {
    patched = null;
    await TestBed.configureTestingModule({
      imports: [DisciplinePage],
      providers: [
        provideHttpClient(),
        provideRouter([{ path: 'forms/:id', component: DisciplinePage }]),
        {
          provide: ApiService,
          useValue: {
            hid: () => 'h1',
            timezone: () => 'America/Chicago',
            get: (path: string) => {
              if (path.includes('/members')) {
                return of([{ id: 'm1', legal_name: 'Jordan Lee' }]);
              }
              return of([NOTE]);
            },
            post: () => of({ id: 'd2', log_entry_id: 'log-2' }),
            patch: (path: string, body: unknown) => {
              patched = { path, body };
              return of({ ...NOTE, ...((body as object) ?? {}), id: 'd1' });
            },
          },
        },
        { provide: AuthService, useValue: { can: () => true } },
      ],
    }).compileComponents();
  });

  it('lets you view a saved behavior note and open the submitted form', async () => {
    const fixture = TestBed.createComponent(DisciplinePage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).toContain('Threw pencil');
    const view = host.querySelector('[data-test="view-behavior"]') as HTMLButtonElement;
    expect(view).toBeTruthy();
    view.click();
    fixture.detectChanges();
    expect(host.textContent).toContain('Asked to do homework');
    expect(host.textContent).toContain('Cool-down in room');
    expect(host.textContent).toContain('Lost screen time');
    expect(host.textContent).toContain('Case worker');
    const formLink = host.querySelector('[data-test="view-behavior-form"]') as HTMLAnchorElement;
    expect(formLink).toBeTruthy();
    expect(formLink.getAttribute('href')).toContain('/forms/log-1');
  });

  it('lets you edit a saved behavior note', async () => {
    const fixture = TestBed.createComponent(DisciplinePage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    const edit = host.querySelector('[data-test="edit-behavior"]') as HTMLButtonElement;
    expect(edit).toBeTruthy();
    edit.click();
    fixture.detectChanges();
    const page = fixture.componentInstance;
    expect(page.draft.behavior).toBe('Threw pencil');
    page.draft.behavior = 'Threw pencil and yelled';
    page.save();
    expect(patched?.path).toBe('/households/h1/discipline/d1');
    const body = patched?.body as { behavior: string };
    expect(body.behavior).toBe('Threw pencil and yelled');
  });
});
