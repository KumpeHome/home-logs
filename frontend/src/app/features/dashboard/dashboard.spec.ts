import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { signal } from '@angular/core';
import { of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { DashboardPage } from './dashboard';

const apiMock = {
  hid: () => 'h1',
  timezone: () => 'America/Chicago',
  get: () =>
    of({
      active_members: 3,
      inactive_members: 0,
      drafts: 0,
      meds_due: [],
      recent_logs: [],
    }),
  post: () => of({ id: 'h1' }),
};

describe('DashboardPage', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DashboardPage],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        { provide: ApiService, useValue: apiMock },
        {
          provide: AuthService,
          useValue: {
            householdId: signal('h1'),
            me: signal({ name: 'Sam Kumpe', email: 'sam@example.com' }),
            can: () => true,
          },
        },
      ],
    }).compileComponents();
  });

  it('greets the household by first name and shows what needs attention', async () => {
    const fixture = TestBed.createComponent(DashboardPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toMatch(/Good (morning|afternoon|evening), Sam/);
    expect(text).toContain("Here's what needs your attention today.");
    expect(text).toContain('Add a record');
  });

  it('uses a reassuring empty state when nothing is due', async () => {
    const fixture = TestBed.createComponent(DashboardPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('No medications need attention right now.');
    expect(text).toContain('No recent records yet.');
  });
});
