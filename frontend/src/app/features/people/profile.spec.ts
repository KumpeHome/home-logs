import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { ProfilePage } from './profile';

const PROFILE = {
  id: 'p1',
  member_id: 'm1',
  first_name: 'Casey',
  middle_name: null,
  last_name: 'Child',
  preferred_name: 'Case',
  date_of_birth: '2014-04-02',
  sex: 'female',
  gender: null,
  pronouns: 'she/her',
  has_photo: false,
  medicaid_id: 'MD-9',
  insurance_provider: 'SoonerCare',
  insurance_policy: 'P-1',
  insurance_group: 'G-1',
  placement_start: '2024-01-15',
  placement_end: null,
  school_name: 'Lincoln',
  school_grade: '5',
  teacher: 'Ms. Reed',
  counselor: 'Mr. Hale',
  clothing_shirt: 'M',
  clothing_pants: '10',
  clothing_shoes: '3',
  notes: 'Loves soccer',
  allergies: [{ id: 'a1', allergen: 'Peanuts', severity: 'severe', reaction: 'hives' }],
  medications: [
    {
      id: 'med1',
      name: 'Cetirizine',
      dose: '5mg',
      route: 'oral',
      frequency: 'daily',
      schedule_times: ['08:00'],
      instructions: 'With breakfast',
      is_prn: false,
      is_psychotropic: false,
      prescriber: 'Dr. Lee',
      diagnosis: 'Allergies',
      start_date: '2026-01-01',
      end_date: '2026-12-31',
      hold_reason: null,
      active: true,
      flags: ['drowsy', 'take_with_food'],
    },
    {
      id: 'med2',
      name: 'Old Antibiotic',
      dose: '400mg',
      route: 'oral',
      frequency: 'twice daily',
      schedule_times: ['08:00', '20:00'],
      instructions: 'Finished',
      is_prn: false,
      is_psychotropic: false,
      prescriber: 'Dr. Patel',
      diagnosis: 'Ear infection',
      start_date: '2025-01-01',
      end_date: '2025-01-10',
      hold_reason: null,
      active: false,
      flags: [],
    },
  ],
  otc_medications: [
    { id: 'as1', otc_medication_id: 'o2', name: 'Ibuprofen', dose: '200mg', route: 'oral', is_otc: true },
  ],
  diagnoses: [],
  disabilities: [],
  clinicians: [],
  professional_contacts: [],
  emergency_contacts: [],
};

const MEMBER = {
  id: 'm1',
  household_role: 'child',
  status: 'active',
  login_status: 'none',
  email: null,
  legal_name: 'Casey Child',
  has_photo: false,
};

const apiMock = {
  hid: () => 'h1',
  timezone: () => 'America/Chicago',
  get: (path: string) => {
    if (path.endsWith('/profile')) {
      return of(PROFILE);
    }
    if (path.endsWith('/members/m1')) {
      return of(MEMBER);
    }
    if (path.includes('/otc-medications')) {
      return of([
        { id: 'o1', name: 'Acetaminophen', dose: '325mg', route: 'oral' },
        { id: 'o2', name: 'Ibuprofen', dose: '200mg', route: 'oral' },
      ]);
    }
    return of([]);
  },
  post: () => of({}),
  patch: () => of(PROFILE),
  delete: () => of(undefined),
  upload: () => of(PROFILE),
};

describe('ProfilePage', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProfilePage],
      providers: [
        provideHttpClient(),
        provideRouter([{ path: 'people/:id', component: ProfilePage }]),
        { provide: ApiService, useValue: apiMock },
      ],
    }).compileComponents();
    await TestBed.inject(Router).navigateByUrl('/people/m1');
  });

  it('shows a read-only dossier with tabs instead of a permanent edit form', async () => {
    const fixture = TestBed.createComponent(ProfilePage);
    fixture.detectChanges();
    await fixture.whenStable();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Casey Child');
    expect(text).toContain('Overview');
    expect(text).toContain('Health');
    expect(text).toContain('School');
    expect(text).toContain('Team');
    expect(text).toContain('Records');
    expect(text).toContain('she/her');
    expect(text).toContain('SoonerCare');
    expect(text).not.toContain('Add medication');
    expect(fixture.nativeElement.querySelector('[data-test="edit-overview"]')?.textContent).toContain(
      'Edit',
    );
  });

  it('reveals an add form when Add is clicked on a health section', async () => {
    const fixture = TestBed.createComponent(ProfilePage);
    fixture.detectChanges();
    await fixture.whenStable();
    const host = fixture.nativeElement as HTMLElement;
    const healthTab = Array.from(host.querySelectorAll('button')).find((btn) =>
      btn.textContent?.includes('Health'),
    );
    healthTab?.click();
    fixture.detectChanges();
    expect(host.textContent).toContain('Peanuts');
    const addMed = host.querySelector('[data-test="add-medications"]') as HTMLButtonElement;
    expect(addMed).toBeTruthy();
    addMed.click();
    fixture.detectChanges();
    expect(host.querySelector('[data-test="add-medications-form"]')).toBeTruthy();
  });

  it('lets a caregiver assign household OTC meds in addition to person-specific meds', async () => {
    const fixture = TestBed.createComponent(ProfilePage);
    fixture.detectChanges();
    await fixture.whenStable();
    const host = fixture.nativeElement as HTMLElement;
    const healthTab = Array.from(host.querySelectorAll('button')).find((btn) =>
      btn.textContent?.includes('Health'),
    );
    healthTab?.click();
    fixture.detectChanges();
    expect(host.textContent).toContain('Household OTC');
    expect(host.textContent).toContain('Ibuprofen');
    expect(host.querySelector('[data-test="assign-otc"]')).toBeTruthy();
    expect(host.textContent).toContain('Acetaminophen');
  });

  it('shows full medication details, edit, dates, flags, and active/inactive filters', async () => {
    const fixture = TestBed.createComponent(ProfilePage);
    fixture.detectChanges();
    await fixture.whenStable();
    const host = fixture.nativeElement as HTMLElement;
    const healthTab = Array.from(host.querySelectorAll('button')).find((btn) =>
      btn.textContent?.includes('Health'),
    );
    healthTab?.click();
    fixture.detectChanges();
    expect(host.querySelector('[data-test="med-filter"]')).toBeTruthy();
    expect(host.textContent).toContain('Cetirizine');
    expect(host.textContent).toContain('Dr. Lee');
    expect(host.textContent).toContain('Allergies');
    expect(host.textContent).toContain('2026-01-01');
    expect(host.textContent).toContain('Drowsy');
    expect(host.textContent).toContain('Take with food');
    expect(host.textContent).not.toContain('Old Antibiotic');
    const inactive = host.querySelector('[data-test="med-filter-inactive"]') as HTMLButtonElement;
    inactive.click();
    fixture.detectChanges();
    expect(host.textContent).toContain('Old Antibiotic');
    const edit = host.querySelector('[data-test="edit-medication"]') as HTMLButtonElement;
    expect(edit).toBeTruthy();
    edit.click();
    fixture.detectChanges();
    expect(host.querySelector('[data-test="edit-medications-form"]')).toBeTruthy();
    expect(host.querySelector('[data-test="med-start-date"]')).toBeTruthy();
    expect(host.querySelector('[data-test="med-end-date"]')).toBeTruthy();
  });

  it('asks for a dose amount and unit instead of a single dose string', async () => {
    const fixture = TestBed.createComponent(ProfilePage);
    fixture.detectChanges();
    await fixture.whenStable();
    const host = fixture.nativeElement as HTMLElement;
    const healthTab = Array.from(host.querySelectorAll('button')).find((btn) =>
      btn.textContent?.includes('Health'),
    );
    healthTab?.click();
    fixture.detectChanges();
    const addMed = host.querySelector('[data-test="add-medications"]') as HTMLButtonElement;
    addMed.click();
    fixture.detectChanges();
    expect(host.querySelector('[data-test="med-dose-amount"]')).toBeTruthy();
    expect(host.querySelector('[data-test="med-dose-unit"]')).toBeTruthy();
    expect(host.querySelector('input[name="mdose"]')).toBeNull();
  });
});

describe('ProfilePage permissions', () => {
  it('lets a household admin grant form and tab permissions', async () => {
    const posted: { path?: string; body?: any } = {};
    const { AuthService } = await import('../../core/auth.service');
    await TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ProfilePage],
      providers: [
        provideHttpClient(),
        provideRouter([{ path: 'people/:id', component: ProfilePage }]),
        {
          provide: ApiService,
          useValue: {
            hid: () => 'h1',
            timezone: () => 'America/Chicago',
            get: (path: string) => {
              if (path === '/permission-catalog') {
                return of([
                  { code: 'tab.school', name: 'School', group: 'tab', actions: ['view', 'add', 'edit'] },
                  {
                    code: 'form.sibling_contact',
                    name: 'Sibling Contact',
                    group: 'form',
                    actions: ['view', 'add', 'edit', 'export'],
                  },
                ]);
              }
              if (path.endsWith('/permissions')) {
                return of([{ resource: 'tab.school', action: 'view' }]);
              }
              if (path.includes('/profile')) {
                return of({ ...PROFILE, member_id: 'm2' });
              }
              if (path.includes('/members/') && !path.includes('/permissions')) {
                return of({
                  id: 'm2',
                  household_role: 'adult',
                  status: 'active',
                  login_status: 'linked',
                  email: 'sam@example.com',
                  legal_name: 'Sam Helper',
                  has_photo: false,
                });
              }
              return of([]);
            },
            put: (path: string, body: unknown) => {
              posted.path = path;
              posted.body = body;
              return of([]);
            },
            post: () => of({}),
            patch: () => of({}),
            delete: () => of(undefined),
            upload: () => of({}),
          },
        },
      ],
    }).compileComponents();
    const auth = TestBed.inject(AuthService);
    auth.householdId.set('h1');
    auth.me.set({
      subject: 'ada',
      email: 'ada@example.com',
      name: 'Ada',
      scopes: [],
      linked: true,
      pending_memberships: [],
      households: [
        {
          id: 'h1',
          name: 'Home',
          household_type: 'foster',
          timezone: 'America/Chicago',
          household_role: 'admin',
          permissions: [],
        },
      ],
    });
    await TestBed.inject(Router).navigateByUrl('/people/m2');
    const fixture = TestBed.createComponent(ProfilePage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    const tab = Array.from(host.querySelectorAll('button')).find((btn) =>
      btn.textContent?.includes('Permissions'),
    );
    expect(tab).toBeTruthy();
    tab?.click();
    fixture.detectChanges();
    expect(host.textContent).toContain('School');
    expect(host.textContent).toContain('Sibling Contact');
    expect(host.querySelector('[data-test="perm-tab.school-view"]')).toBeTruthy();
    const addBox = host.querySelector('[data-test="perm-form.sibling_contact-add"]') as HTMLInputElement;
    expect(addBox).toBeTruthy();
    addBox.click();
    fixture.detectChanges();
    const save = host.querySelector('[data-test="save-permissions"]') as HTMLButtonElement;
    save.click();
    expect(posted.path).toContain('/permissions');
    expect(posted.body.grants).toEqual(
      expect.arrayContaining([
        { resource: 'tab.school', action: 'view' },
        { resource: 'form.sibling_contact', action: 'add' },
      ]),
    );
  });
});
