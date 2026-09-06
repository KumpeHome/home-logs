import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { PAPER_SCAN_ENGINE_LOADER } from '../../shared/paper-scan';
import { DocumentsPage } from './documents';

describe('DocumentsPage', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DocumentsPage],
      providers: [
        provideHttpClient(),
        {
          provide: ApiService,
          useValue: {
            hid: () => 'h1',
            get: () => of([]),
            upload: () => of({ id: 'd1' }),
          },
        },
        { provide: PAPER_SCAN_ENGINE_LOADER, useValue: async () => ({}) },
      ],
    }).compileComponents();
  });

  it('lets you scan a paper with the camera instead of only picking a file', async () => {
    const fixture = TestBed.createComponent(DocumentsPage);
    fixture.detectChanges();
    await fixture.whenStable();
    (fixture.nativeElement as HTMLElement)
      .querySelector('button.hl-btn')
      ?.dispatchEvent(new Event('click'));
    fixture.componentInstance.adding.set(true);
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.querySelector('[data-test="scan-document"]')).toBeTruthy();
    expect(host.textContent).toContain('Scan with camera');
    expect(host.querySelector('hl-document-input')).toBeTruthy();
  });
});
