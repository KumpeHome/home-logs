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
      refills_needed: [],
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

describe('DashboardPage refill reminders', () => {
  it('lists medications that are at the refill reminder level', async () => {
    await TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [DashboardPage],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        {
          provide: ApiService,
          useValue: {
            hid: () => 'h1',
            timezone: () => 'America/Chicago',
            get: () =>
              of({
                active_members: 1,
                inactive_members: 0,
                drafts: 0,
                meds_due: [],
                refills_needed: [
                  {
                    member_id: 'm1',
                    member_name: 'Sam Kid',
                    medication_id: 'med1',
                    medication_name: 'Sertraline',
                    quantity_on_hand: 6,
                    refill_reminder_level: 10,
                    is_otc: false,
                  },
                ],
                recent_logs: [],
              }),
            post: () => of({ id: 'h1' }),
          },
        },
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
    const fixture = TestBed.createComponent(DashboardPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Refills needed');
    expect(text).toContain('Sertraline');
    expect(text).toContain('Sam Kid');
    expect(text).toContain('6 on hand');
  });
});
