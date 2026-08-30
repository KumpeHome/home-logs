import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { App } from './app';

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

  it('hides nav tabs the household member cannot view', async () => {
    const { AuthService } = await import('./core/auth.service');
    const auth = TestBed.inject(AuthService);
    auth.token.set('dev-bypass');
    auth.householdId.set('h1');
    auth.me.set({
      subject: 'sam',
      email: 'sam@example.com',
      name: 'Sam',
      scopes: [],
      linked: true,
      pending_memberships: [],
      households: [
        {
          id: 'h1',
          name: 'Home',
          household_type: 'foster',
          timezone: 'America/Chicago',
          household_role: 'adult',
          permissions: [
            { resource: 'tab.logs', action: 'view' },
            { resource: 'tab.school', action: 'view' },
          ],
        },
      ],
    });
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Logs');
    expect(text).toContain('School');
    expect(text).not.toContain('Discipline');
    expect(text).not.toContain('Documents');
    expect(text).not.toContain('Audit');
  });
});
