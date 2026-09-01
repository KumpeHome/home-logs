import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { AuthService } from '../core/auth.service';
import { LoginPage } from './login';

describe('LoginPage', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoginPage],
      providers: [
        {
          provide: AuthService,
          useValue: {
            login: () => undefined,
            bypassAvailable: signal(false),
          },
        },
      ],
    }).compileComponents();
  });

  it('uses the WebP brand logo and a calm invitation', () => {
    const fixture = TestBed.createComponent(LoginPage);
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    const logo = host.querySelector('[data-test="brand-logo"]') as HTMLImageElement;
    expect(logo).toBeTruthy();
    expect(logo.getAttribute('src')).toContain('.webp');
    expect(logo.getAttribute('src')).not.toContain('.png');
    expect(host.textContent).toContain('Your home. Your records. One secure place.');
    expect(host.textContent).toContain('Sign in');
  });
});
