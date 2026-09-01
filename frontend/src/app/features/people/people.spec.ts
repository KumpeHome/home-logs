import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { PeoplePage } from './people';

describe('PeoplePage', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PeoplePage],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        {
          provide: ApiService,
          useValue: {
            hid: () => 'h1',
            get: () => of([]),
            post: () => of({}),
          },
        },
        {
          provide: AuthService,
          useValue: { can: () => true },
        },
      ],
    }).compileComponents();
  });

  it('keeps add-member tucked away until asked and shows a helpful empty state', async () => {
    const fixture = TestBed.createComponent(PeoplePage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).toContain('No household members yet');
    expect(host.querySelector('form')).toBeNull();
    const add = host.querySelector('[data-test="add-member"]') as HTMLButtonElement;
    expect(add).toBeTruthy();
    add.click();
    fixture.detectChanges();
    expect(host.querySelector('form')).toBeTruthy();
    expect(host.textContent).toContain('First');
  });
});
