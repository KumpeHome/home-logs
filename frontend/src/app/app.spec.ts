import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { App } from './app';
import { AuthService, type MeResponse } from './core/auth.service';

function signIn(
  auth: AuthService,
  overrides: Partial<MeResponse['households'][number]> = {},
): void {
  auth.token.set('dev-bypass');
  auth.householdId.set('h1');
  auth.me.set({
    subject: 'sam',
    email: 'sam@example.com',
    name: 'Sam Kumpe',
    scopes: [],
    linked: true,
    pending_memberships: [],
    households: [
      {
        id: 'h1',
        name: 'Our Home',
        household_type: 'foster',
        timezone: 'America/Chicago',
        household_role: 'admin',
        permissions: [],
        ...overrides,
      },
    ],
  });
}

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter([]), provideHttpClient()],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render the Home Logs brand when signed out', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    expect(fixture.nativeElement).toBeTruthy();
  });

  it('uses the WebP brand logo and grouped navigation when signed in', async () => {
    signIn(TestBed.inject(AuthService));
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    const logo = host.querySelector('[data-test="brand-logo"]') as HTMLImageElement;
    expect(logo).toBeTruthy();
    expect(logo.getAttribute('src')).toContain('.webp');
    expect(logo.getAttribute('src')).not.toContain('.png');
    expect(host.textContent).toContain('Kumpe Home Logs');
    expect(host.textContent).toContain('Add a record');
    expect(host.textContent).toContain('Care');
    expect(host.textContent).toContain('Members');
    expect(host.querySelector('[data-test="open-nav"]')).toBeTruthy();
  });

  it('keeps sidebar links compact in a scrollable nav region', async () => {
    signIn(TestBed.inject(AuthService));
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    const sidebar = host.querySelector('[data-test="app-sidebar"]') as HTMLElement;
    const nav = host.querySelector('[data-test="app-nav"]') as HTMLElement;
    expect(sidebar).toBeTruthy();
    expect(nav).toBeTruthy();
    const labels = [...nav.querySelectorAll('a')].map((el) => el.textContent?.trim());
    expect(labels).toEqual([
      'Dashboard',
      'Members',
      'Logs',
      'School',
      'Behavior',
      'Submitted',
      'Documents',
      'Reports',
      'Activity',
      'Settings',
    ]);
    const navStyle = getComputedStyle(nav);
    expect(navStyle.overflowY).toBe('auto');
    expect(navStyle.display).toBe('flex');
    const sidebarStyle = getComputedStyle(sidebar);
    expect(sidebarStyle.alignSelf).toBe('start');
    expect(sidebarStyle.overflowY).toBe('auto');
  });

  it('hides nav tabs the household member cannot view', async () => {
    signIn(TestBed.inject(AuthService), {
      name: 'Home',
      household_role: 'adult',
      permissions: [
        { resource: 'tab.logs', action: 'view' },
        { resource: 'tab.school', action: 'view' },
      ],
    });
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Logs');
    expect(text).toContain('School');
    expect(text).toContain('Care');
    expect(text).not.toContain('Behavior');
    expect(text).not.toContain('Documents');
    expect(text).not.toContain('Activity');
  });
});
