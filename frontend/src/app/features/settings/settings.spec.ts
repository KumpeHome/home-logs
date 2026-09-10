import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { of, Subject } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { SettingsPage } from './settings';

const apiMock = {
  hid: () => 'h1',
  get: (path: string) => {
    if (path.endsWith('/households/h1')) {
      return of({
        id: 'h1',
        name: 'Kumpe Home',
        household_type: 'family',
        timezone: 'America/Chicago',
      });
    }
    if (path.includes('/otc-medications')) {
      return of([
        { id: 'o1', name: 'Acetaminophen', dose: '325mg', route: 'oral', instructions: 'Fever' },
      ]);
    }
    return of([]);
  },
  post: vi.fn(() => of({ id: 'o2' })),
  patch: vi.fn(() => of({})),
  delete: () => of(undefined),
} as const;

describe('SettingsPage', () => {
  beforeEach(async () => {
    apiMock.patch.mockClear();
    apiMock.post.mockClear();
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
    const units = Array.from(
      fixture.nativeElement.querySelectorAll('[data-test="otc-dose-unit"] option'),
    ).map((option) => (option as HTMLOptionElement).textContent?.trim());
    expect(units).toContain('gummy');
  });

  it('lets you edit a household OTC medication', async () => {
    const fixture = TestBed.createComponent(SettingsPage);
    fixture.detectChanges();
    await fixture.whenStable();
    const host = fixture.nativeElement as HTMLElement;
    const edit = host.querySelector('[data-test="edit-otc"]') as HTMLButtonElement;
    expect(edit).toBeTruthy();
    edit.click();
    fixture.detectChanges();
    const page = fixture.componentInstance;
    expect(page.otcDraft.name).toBe('Acetaminophen');
    expect(page.otcDraft.dose_amount).toBe('325');
    expect(page.otcDraft.dose_unit).toBe('mg');
    expect(host.querySelector('[data-test="save-otc"]')?.textContent).toContain('Save changes');
    page.otcDraft.name = 'Acetaminophen Extra';
    page.otcDraft.dose_unit = 'gummy';
    (host.querySelector('[data-test="save-otc"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    await fixture.whenStable();
    expect(apiMock.patch).toHaveBeenCalled();
    const [path, body] = apiMock.patch.mock.calls[0] as unknown as [
      string,
      { name: string; dose: string },
    ];
    expect(path).toBe('/households/h1/otc-medications/o1');
    expect(body).toEqual(
      expect.objectContaining({ name: 'Acetaminophen Extra', dose: '325gummy' }),
    );
    fixture.detectChanges();
    expect(page.otcDraft.name).toBe('');
    expect(host.querySelector('[data-test="form-success"]')?.textContent).toContain('saved');
  });

  it('disables household OTC save while processing', async () => {
    const pending = new Subject<unknown>();
    apiMock.patch.mockReturnValueOnce(pending as never);
    const fixture = TestBed.createComponent(SettingsPage);
    fixture.detectChanges();
    await fixture.whenStable();
    const host = fixture.nativeElement as HTMLElement;
    (host.querySelector('[data-test="edit-otc"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    (host.querySelector('[data-test="save-otc"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    const button = host.querySelector('[data-test="save-otc"]') as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(host.querySelector('[data-test="form-busy"]')).toBeTruthy();
    pending.next({});
    pending.complete();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(host.querySelector('[data-test="form-success"]')).toBeTruthy();
  });
});
