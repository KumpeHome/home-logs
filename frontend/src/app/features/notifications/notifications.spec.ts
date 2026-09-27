import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { NotificationsPage } from './notifications';

const parentSettings = {
  member_id: 'p1',
  member_name: 'Ada Admin',
  household_role: 'admin',
  email: 'ada@example.com',
  email_enabled: true,
  pushover_enabled: false,
  pushover_connected: false,
  pushover_key_source: null,
  pushover_subscription_available: true,
  dose_lead_minutes: 15,
  subscriptions: [],
  subjects: [
    { id: 'p1', name: 'Ada Admin', kind: 'member' },
    { id: 'c1', name: 'Casey Child', kind: 'member' },
    { id: 'c2', name: 'Sam Kid', kind: 'member' },
    { id: null, name: 'Medicine cabinet', kind: 'household' },
  ],
  topics: [
    {
      code: 'meds.dose_due',
      name: 'Dose reminders',
      description: 'Scheduled doses',
      applies_to: 'member',
    },
    {
      code: 'meds.refill_needed',
      name: 'Refill reminders',
      description: 'Low stock',
      applies_to: 'any',
    },
  ],
  configurable_members: [
    { id: 'p1', name: 'Ada Admin', household_role: 'admin' },
    { id: 'c1', name: 'Casey Child', household_role: 'child' },
  ],
};

const childSettings = {
  ...parentSettings,
  member_id: 'c1',
  member_name: 'Casey Child',
  household_role: 'child',
  email: 'casey@example.com',
  subjects: [
    { id: 'c1', name: 'Casey Child', kind: 'member' },
    { id: null, name: 'Medicine cabinet', kind: 'household' },
  ],
  configurable_members: [{ id: 'c1', name: 'Casey Child', household_role: 'child' }],
};

describe('NotificationsPage', () => {
  const api = {
    hid: () => 'h1',
    get: vi.fn(),
    put: vi.fn(),
    post: vi.fn(),
  };

  async function setup(params: Record<string, string> = {}, settings = parentSettings) {
    api.get.mockReset();
    api.put.mockReset();
    api.post.mockReset();
    api.get.mockImplementation(() => of(settings));
    api.put.mockImplementation(() => of(settings));
    api.post.mockImplementation((path: unknown) => {
      const url = String(path);
      if (url.endsWith('/pushover/start')) {
        return of({ subscribe_url: 'https://pushover.net/subscribe/HomeLogs-abc' });
      }
      if (url.endsWith('/notifications/test')) {
        return of({
          deliveries: [
            { channel: 'email', status: 'sent' },
            { channel: 'pushover', status: 'sent' },
          ],
        });
      }
      return of({ ...settings, pushover_connected: true, pushover_key_source: 'subscription' });
    });
    await TestBed.configureTestingModule({
      imports: [NotificationsPage],
      providers: [
        provideHttpClient(),
        provideRouter([
          { path: 'notifications', component: NotificationsPage },
          { path: 'notifications/pushover', component: NotificationsPage },
        ]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap(params) } },
        },
        { provide: ApiService, useValue: api },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(NotificationsPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => TestBed.resetTestingModule());

  it('lets a parent configure their own reminders and a child', async () => {
    const fixture = await setup();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).toContain('Notifications');
    expect(host.textContent).toContain('Casey Child');
    expect(host.querySelector('[data-test="notification-member"]')).toBeTruthy();
    expect(host.querySelector('[data-test="subscribe-pushover"]')).toBeTruthy();
    expect(host.querySelector('[data-test="pushover-user-key"]')).toBeTruthy();
    expect(host.textContent).toContain('Medicine cabinet');
    const dose = host.querySelector('[data-test="sub-meds.dose_due-c1"]') as HTMLInputElement;
    const cabinet = host.querySelector(
      '[data-test="sub-meds.refill_needed-household"]',
    ) as HTMLInputElement;
    dose.click();
    cabinet.click();
    fixture.detectChanges();
    (host.querySelector('[data-test="save-notifications"]') as HTMLButtonElement).click();
    await fixture.whenStable();

    expect(api.put).toHaveBeenCalledWith(
      '/households/h1/notifications',
      expect.objectContaining({
        member_id: 'p1',
        subscriptions: expect.arrayContaining([
          { topic: 'meds.dose_due', subject_member_id: 'c1' },
          { topic: 'meds.refill_needed', subject_member_id: null },
        ]),
      }),
    );
  });

  it('hides other people when a child is configuring their own notifications', async () => {
    api.get.mockImplementation(() => of(childSettings));
    const fixture = await setup({}, childSettings);
    const host = fixture.nativeElement as HTMLElement;
    expect(host.querySelector('[data-test="notification-member"]')).toBeNull();
    expect(host.textContent).toContain('Casey Child');
    expect(host.querySelector('[data-test="sub-meds.dose_due-c1"]')).toBeTruthy();
    expect(host.querySelector('[data-test="sub-meds.dose_due-p1"]')).toBeNull();
  });

  it('starts a Pushover subscription and still offers a user key', async () => {
    const fixture = await setup();
    const assign = vi
      .spyOn(fixture.componentInstance, 'openUrl')
      .mockImplementation(() => undefined);
    const subscribe = fixture.nativeElement.querySelector(
      '[data-test="subscribe-pushover"]',
    ) as HTMLAnchorElement;
    expect(subscribe.tagName).toBe('A');
    expect(subscribe.classList.contains('pushover_button')).toBe(true);
    expect(subscribe.textContent?.trim()).toBe('Subscribe With Pushover');
    subscribe.click();
    await fixture.whenStable();
    expect(api.post).toHaveBeenCalledWith('/households/h1/notifications/pushover/start', {
      member_id: 'p1',
    });
    expect(assign).toHaveBeenCalledWith('https://pushover.net/subscribe/HomeLogs-abc');
  });

  it('keeps each child on one row and can notify about one child only', async () => {
    const fixture = await setup();
    const host = fixture.nativeElement as HTMLElement;
    const emailLabel = host
      .querySelector('[data-test="email-enabled"]')
      ?.closest('label') as HTMLElement;
    const doseLabel = host
      .querySelector('[data-test="sub-meds.dose_due-c1"]')
      ?.closest('label') as HTMLElement;
    expect(getComputedStyle(emailLabel).display).toBe('flex');
    expect(getComputedStyle(emailLabel).flexDirection).toBe('row');
    expect(getComputedStyle(doseLabel).display).toBe('flex');
    expect(getComputedStyle(doseLabel).flexDirection).toBe('row');
    const names = [...host.querySelectorAll('[data-test="reminder-who"]')].map((row) =>
      row.textContent?.trim(),
    );
    expect(names).toEqual(['Ada Admin', 'Casey Child', 'Sam Kid', 'Medicine cabinet']);
    (host.querySelector('[data-test="sub-meds.dose_due-c1"]') as HTMLInputElement).click();
    fixture.detectChanges();
    (host.querySelector('[data-test="save-notifications"]') as HTMLButtonElement).click();
    await fixture.whenStable();
    const body = api.put.mock.calls.at(-1)?.[1] as {
      subscriptions: { topic: string; subject_member_id: string | null }[];
    };
    expect(body.subscriptions).toEqual([{ topic: 'meds.dose_due', subject_member_id: 'c1' }]);
    expect(body.subscriptions.some((item) => item.subject_member_id === 'c2')).toBe(false);
  });

  it('sends a test notification for the person being configured', async () => {
    const fixture = await setup();
    (fixture.nativeElement.querySelector('[data-test="send-test"]') as HTMLButtonElement).click();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(api.post).toHaveBeenCalledWith('/households/h1/notifications/test', {
      member_id: 'p1',
    });
    expect(fixture.nativeElement.textContent).toContain('Test sent by email and Pushover');
  });

  it('stores the Pushover subscription key when Pushover redirects back', async () => {
    await setup({
      member: 'c1',
      rand: 'link-token',
      pushover_user_key: 'sFromPushover',
    });
    expect(api.post).toHaveBeenCalledWith('/households/h1/notifications/pushover/complete', {
      member_id: 'c1',
      rand: 'link-token',
      pushover_user_key: 'sFromPushover',
      pushover_unsubscribed: false,
    });
  });
});
