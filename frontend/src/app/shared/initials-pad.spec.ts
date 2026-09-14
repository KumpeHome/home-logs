import { TestBed } from '@angular/core/testing';
import { InitialsPad } from './initials-pad';

describe('InitialsPad', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InitialsPad],
    }).compileComponents();
  });

  it('uses a high-resolution canvas so exported initials stay sharp', async () => {
    const fixture = TestBed.createComponent(InitialsPad);
    fixture.detectChanges();
    await fixture.whenStable();
    const canvas = fixture.nativeElement.querySelector('canvas') as HTMLCanvasElement;
    expect(canvas.width).toBeGreaterThanOrEqual(480);
    expect(canvas.height).toBeGreaterThanOrEqual(180);
  });
});
