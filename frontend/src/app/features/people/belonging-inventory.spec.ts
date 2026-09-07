import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { BelongingInventory } from './belonging-inventory';

const FORM_TYPES = [
  {
    code: 'personal_belonging',
    schema: {
      properties: {
        item_category: { type: 'string', title: 'Item', enum: ['Shoes', 'Jackets', 'Other'] },
      },
    },
  },
];

const SHOE = {
  id: 'b1',
  form_type_code: 'personal_belonging',
  status: 'submitted',
  payload: {
    item_category: 'Shoes',
    description: 'Nike size 5',
    quantity: 1,
    recorded_on: '2026-08-19',
    initials: 'JK',
    disposition: '',
  },
};

describe('BelongingInventory', () => {
  let fixture: ComponentFixture<BelongingInventory>;
  let posted: { path: string; body: unknown } | null;
  let items: unknown[];

  beforeEach(async () => {
    posted = null;
    items = [SHOE];
    await TestBed.configureTestingModule({
      imports: [BelongingInventory],
      providers: [
        {
          provide: ApiService,
          useValue: {
            get: (path: string) => {
              if (path === '/form-types') {
                return of(FORM_TYPES);
              }
              return of(items);
            },
            post: (path: string, body: unknown) => {
              posted = { path, body };
              return of({ id: 'b2' });
            },
            patch: (path: string, body: unknown) => {
              posted = { path, body };
              return of({ id: 'b1' });
            },
          },
        },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(BelongingInventory);
    fixture.componentRef.setInput('householdId', 'h1');
    fixture.componentRef.setInput('memberId', 'm1');
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  });

  it('shows the current inventory for the person', () => {
    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).toContain('Personal belonging inventory');
    expect(host.textContent).toContain('Shoes');
    expect(host.textContent).toContain('Nike size 5');
    expect(host.querySelector('[data-test="add-belonging"]')).toBeTruthy();
    expect(host.querySelector('[data-test="edit-belonging"]')).toBeTruthy();
  });

  it('hides superseded amendments so only the current item remains', async () => {
    items = [
      { ...SHOE, id: 'old', status: 'amended' },
      {
        ...SHOE,
        id: 'b1',
        status: 'submitted',
        payload: { ...SHOE.payload, description: 'Nike size 6' },
      },
    ];
    fixture.componentInstance.reload();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).toContain('Nike size 6');
    expect(host.textContent).not.toContain('Nike size 5');
  });

  it('adds a belonging item for this person', async () => {
    const host = fixture.nativeElement as HTMLElement;
    (host.querySelector('[data-test="add-belonging"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(host.querySelector('[data-test="belonging-form"]')).toBeTruthy();
    const page = fixture.componentInstance;
    page.draft.item_category = 'Jackets';
    page.draft.description = 'Winter coat';
    page.draft.quantity = 1;
    page.draft.recorded_on = '2026-09-07';
    page.draft.initials = 'JK';
    page.save();
    await fixture.whenStable();
    expect(posted?.path).toBe('/households/h1/logs');
    const body = posted?.body as {
      form_type_code: string;
      subject_member_id: string;
      submit: boolean;
      payload: Record<string, unknown>;
    };
    expect(body.form_type_code).toBe('personal_belonging');
    expect(body.subject_member_id).toBe('m1');
    expect(body.submit).toBe(true);
    expect(body.payload['item_category']).toBe('Jackets');
    expect(body.payload['description']).toBe('Winter coat');
    expect(body.payload['quantity']).toBe(1);
  });

  it('saves edits to an existing submitted item', async () => {
    const host = fixture.nativeElement as HTMLElement;
    (host.querySelector('[data-test="edit-belonging"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(host.querySelector('[data-test="belonging-form"]')).toBeTruthy();
    const page = fixture.componentInstance;
    page.draft.description = 'Nike size 6';
    page.draft.quantity = 2;
    page.save();
    await fixture.whenStable();
    expect(posted?.path).toBe('/households/h1/logs/b1/amend');
    const body = posted?.body as { reason: string; payload: Record<string, unknown> };
    expect(body.reason).toContain('inventory');
    expect(body.payload['description']).toBe('Nike size 6');
    expect(body.payload['quantity']).toBe(2);
    expect(body.payload['item_category']).toBe('Shoes');
  });
});

describe('BelongingInventory load errors', () => {
  it('shows an error when belonging logs cannot be loaded', async () => {
    await TestBed.configureTestingModule({
      imports: [BelongingInventory],
      providers: [
        {
          provide: ApiService,
          useValue: {
            get: (path: string) => {
              if (path === '/form-types') {
                return of(FORM_TYPES);
              }
              return throwError(() => ({ status: 403 }));
            },
          },
        },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(BelongingInventory);
    fixture.componentRef.setInput('householdId', 'h1');
    fixture.componentRef.setInput('memberId', 'm1');
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).not.toContain('Nike size 5');
    expect(host.querySelector('.error')?.textContent).toMatch(/could not load/i);
  });
});
