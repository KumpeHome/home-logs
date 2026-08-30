import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormRenderer } from './form-renderer';

describe('FormRenderer', () => {
  let fixture: ComponentFixture<FormRenderer>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FormRenderer],
    }).compileComponents();
    fixture = TestBed.createComponent(FormRenderer);
    fixture.componentRef.setInput('schema', {
      type: 'object',
      properties: {
        meeting_point: { type: 'string', title: 'Meeting point' },
      },
    });
    await fixture.whenStable();
  });

  it('renders schema field titles', () => {
    expect(fixture.nativeElement.textContent).toContain('Meeting point');
  });

  it('renders a checkbox for each household member', async () => {
    fixture.componentRef.setInput('schema', {
      type: 'object',
      properties: {
        participants: {
          type: 'array',
          title: 'Members participating',
          items: { type: 'string' },
          'x-widget': 'member-checkboxes',
        },
      },
    });
    fixture.componentRef.setInput('members', [
      { id: 'm1', legal_name: 'Ada Admin' },
      { id: 'm2', legal_name: 'Casey Child' },
    ]);
    fixture.detectChanges();
    await fixture.whenStable();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Ada Admin');
    expect(text).toContain('Casey Child');
    expect(fixture.nativeElement.querySelectorAll('input[type="checkbox"]').length).toBe(2);
  });

  it('lets you select household members for a drill instead of typing names', async () => {
    fixture.componentRef.setInput('schema', {
      type: 'object',
      properties: {
        participants: {
          type: 'array',
          title: 'Members participating',
          items: { type: 'string' },
          format: 'member-ids',
        },
      },
    });
    fixture.componentRef.setInput('members', [
      { id: 'm1', legal_name: 'Ada Admin', household_role: 'admin' },
      { id: 'm2', legal_name: 'Casey Child', household_role: 'child' },
    ]);
    fixture.detectChanges();
    await fixture.whenStable();
    const select = fixture.nativeElement.querySelector(
      'select[multiple]',
    ) as HTMLSelectElement;
    expect(select).toBeTruthy();
    expect(fixture.nativeElement.querySelector('input[type="text"]')).toBeNull();
    const labels = Array.from(select.options).map((option) => option.textContent?.trim());
    expect(labels).toEqual(['Ada Admin', 'Casey Child']);
  });

  it('renders a multi-select of children for visits', async () => {
    fixture.componentRef.setInput('schema', {
      type: 'object',
      properties: {
        children_visited: {
          type: 'array',
          title: 'Children visited',
          items: { type: 'string' },
          'x-widget': 'child-multiselect',
        },
      },
    });
    fixture.componentRef.setInput('members', [
      { id: 'a1', legal_name: 'Ada Admin', household_role: 'admin' },
      { id: 'c1', legal_name: 'Casey Child', household_role: 'child' },
      { id: 'c2', legal_name: 'Sam Kid', household_role: 'child' },
    ]);
    fixture.detectChanges();
    await fixture.whenStable();
    const select = fixture.nativeElement.querySelector('select[multiple]') as HTMLSelectElement;
    expect(select).toBeTruthy();
    const labels = Array.from(select.options).map((option) => option.textContent?.trim());
    expect(labels).toEqual(['Casey Child', 'Sam Kid']);
  });

  it('emits integers and comma-separated lists so HTML forms can save', async () => {
    fixture.componentRef.setInput('schema', {
      type: 'object',
      properties: {
        evacuation_seconds: { type: 'integer', title: 'Seconds to evacuate' },
        attendees: { type: 'array', title: 'Attendees', items: { type: 'string' } },
        overnight: { type: 'boolean', title: 'Overnight' },
      },
    });
    fixture.detectChanges();
    await fixture.whenStable();
    const renderer = fixture.componentInstance;
    renderer.model['evacuation_seconds'] = '47';
    renderer.model['attendees'] = 'Ada, Casey';
    const saved: Record<string, unknown>[] = [];
    renderer.saved.subscribe((payload) => saved.push(payload));
    renderer.emitSave();
    expect(saved[0]['evacuation_seconds']).toBe(47);
    expect(saved[0]['attendees']).toEqual(['Ada', 'Casey']);
    expect(saved[0]['overnight']).toBe(false);
  });
});
