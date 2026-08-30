import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { SettingsPage } from './settings';

const apiMock = {
  hid: () => 'h1',
  get: (path: string) => {
    if (path.endsWith('/households/h1')) {
      return of({ id: 'h1', name: 'Kumpe Home', household_type: 'family', timezone: 'America/Chicago' });
    }
    if (path.includes('/otc-medications')) {
      return of([{ id: 'o1', name: 'Acetaminophen', dose: '325mg', route: 'oral' }]);
    }
    return of([]);
  },
  post: () => of({ id: 'o2' }),
  patch: () => of({}),
  delete: () => of(undefined),
};

describe('SettingsPage', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SettingsPage],
      providers: [
        provideHttpClient(),
        { provide: ApiService, useValue: apiMock },
        { provide: AuthService, useValue: { scopes: () => [] } },
      ],
    }).compileComponents();
  });

  it('lists household over-the-counter medications in a medicine cabinet', async () => {
    const fixture = TestBed.createComponent(SettingsPage);
    fixture.detectChanges();
    await fixture.whenStable();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Medicine cabinet');
    expect(text).toContain('Acetaminophen');
    expect(fixture.nativeElement.querySelector('[data-test="add-otc"]')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('[data-test="otc-dose-amount"]')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('[data-test="otc-dose-unit"]')).toBeTruthy();
  });
});
