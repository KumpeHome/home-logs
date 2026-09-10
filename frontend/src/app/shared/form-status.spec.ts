import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormStatus } from './form-status';

describe('FormStatus', () => {
  let fixture: ComponentFixture<FormStatus>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FormStatus],
    }).compileComponents();
    fixture = TestBed.createComponent(FormStatus);
  });

  it('shows an activity indicator while busy', () => {
    fixture.componentRef.setInput('busy', true);
    fixture.detectChanges();
    const busy = fixture.nativeElement.querySelector('[data-test="form-busy"]');
    expect(busy).toBeTruthy();
    expect(busy.textContent).toContain('Saving');
    expect(fixture.nativeElement.querySelector('[data-test="form-success"]')).toBeNull();
  });

  it('shows a success message when idle', () => {
    fixture.componentRef.setInput('busy', false);
    fixture.componentRef.setInput('success', 'Medication saved.');
    fixture.detectChanges();
    expect(
      fixture.nativeElement.querySelector('[data-test="form-success"]')?.textContent,
    ).toContain('Medication saved.');
  });
});
