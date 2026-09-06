import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DocumentInput } from './document-input';
import { PAPER_SCAN_ENGINE_LOADER, type PaperScanEngine } from './paper-scan';

const PNG_1X1 = Uint8Array.from(
  atob(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  ),
  (ch) => ch.charCodeAt(0),
);

function fakeEngine(): PaperScanEngine {
  return {
    highlightPaper: (image: CanvasImageSource) => {
      const canvas = document.createElement('canvas');
      if (image instanceof HTMLCanvasElement) {
        canvas.width = image.width;
        canvas.height = image.height;
      }
      return canvas;
    },
    extractPaper: (_image: CanvasImageSource, width: number, height: number) => {
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      canvas.toBlob = (callback: BlobCallback) =>
        callback(new Blob([PNG_1X1], { type: 'image/png' }));
      return canvas;
    },
  };
}

describe('DocumentInput', () => {
  let fixture: ComponentFixture<DocumentInput>;
  let getUserMedia: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    getUserMedia = vi.fn(async () => ({
      getTracks: () => [{ stop: () => undefined }],
    }));
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia },
    });
    HTMLMediaElement.prototype.play = async () => undefined;
    HTMLCanvasElement.prototype.toBlob = function toBlob(callback: BlobCallback) {
      callback(new Blob([PNG_1X1], { type: 'image/png' }));
    };
    await TestBed.configureTestingModule({
      imports: [DocumentInput],
      providers: [{ provide: PAPER_SCAN_ENGINE_LOADER, useValue: async () => fakeEngine() }],
    }).compileComponents();
    fixture = TestBed.createComponent(DocumentInput);
    fixture.detectChanges();
  });

  afterEach(() => {
    fixture.destroy();
  });

  it('offers a file picker and a camera scan action', () => {
    const host = fixture.nativeElement as HTMLElement;
    const picker = host.querySelector('[data-test="document-file"]') as HTMLInputElement;
    expect(picker).toBeTruthy();
    expect(picker.getAttribute('accept')).toContain('application/pdf');
    expect(host.querySelector('[data-test="scan-document"]')).toBeTruthy();
    expect(host.textContent).toContain('Scan with camera');
  });

  it('emits a chosen file from the picker', () => {
    const files: File[] = [];
    fixture.componentInstance.fileChange.subscribe((file: File | null) => {
      if (file) files.push(file);
    });
    const chosen = new File(['pdf'], 'court-order.pdf', { type: 'application/pdf' });
    fixture.componentInstance.onFile({
      target: { files: [chosen] },
    } as unknown as Event);
    expect(files[0]).toBe(chosen);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('court-order.pdf');
  });

  it('opens the document scanner and turns captured pages into a PDF', async () => {
    const files: File[] = [];
    fixture.componentInstance.fileChange.subscribe((file: File | null) => {
      if (file) files.push(file);
    });
    const host = fixture.nativeElement as HTMLElement;
    (host.querySelector('[data-test="scan-document"]') as HTMLButtonElement).click();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(getUserMedia).toHaveBeenCalled();
    const constraints = getUserMedia.mock.calls[0][0] as MediaStreamConstraints;
    expect((constraints.video as MediaTrackConstraints).facingMode).toEqual({
      ideal: 'environment',
    });
    expect(host.querySelector('[data-test="scan-dialog"]')).toBeTruthy();
    expect(host.querySelector('[data-test="capture-page"]')).toBeTruthy();
    await fixture.componentInstance.capturePage();
    fixture.detectChanges();
    expect(host.textContent).toContain('1 page');
    await fixture.componentInstance.useScans();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(files.length).toBe(1);
    expect(files[0].type).toBe('application/pdf');
    expect(files[0].name).toMatch(/scan.*\.pdf$/i);
    expect(host.querySelector('[data-test="scan-dialog"]')).toBeNull();
  });
});
