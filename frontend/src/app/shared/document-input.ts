import {
  Component,
  ElementRef,
  NgZone,
  OnDestroy,
  inject,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';
import {
  DOCUMENT_ACCEPT,
  DOCUMENT_CAMERA,
  PAPER_SCAN_ENGINE_LOADER,
  canvasToBlob,
  captureFrame,
  extractOrFallback,
  scanFilename,
  type PaperScanEngine,
} from './paper-scan';

@Component({
  selector: 'hl-document-input',
  template: `
    <div class="file-actions">
      <label class="hl-btn secondary picker">
        Choose file
        <input type="file" [accept]="accept" data-test="document-file" (change)="onFile($event)" />
      </label>
      <button class="hl-btn" type="button" data-test="scan-document" (click)="startScan()">
        Scan with camera
      </button>
    </div>
    @if (selectedName()) {
      <p class="muted" data-test="selected-file">{{ selectedName() }}</p>
    }
    <p class="muted hint">{{ hint() }}</p>
    @if (scanError(); as message) {
      <p class="error">{{ message }}</p>
    }
    @if (scanning()) {
      <div class="scan-dialog" data-test="scan-dialog" role="dialog" aria-label="Scan document">
        <div class="preview">
          <video #preview autoplay muted playsinline></video>
          <canvas #overlay></canvas>
        </div>
        <div class="toolbar">
          <p class="muted">{{ status() }}</p>
          <div class="file-actions">
            <button class="hl-btn" type="button" data-test="capture-page" (click)="capturePage()">
              Capture page
            </button>
            <button
              class="hl-btn secondary"
              type="button"
              data-test="use-scans"
              [disabled]="!pages().length"
              (click)="useScans()"
            >
              Use scans
            </button>
            <button
              class="hl-btn ghost"
              type="button"
              data-test="cancel-scan"
              (click)="cancelScan()"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    }
  `,
  styles: `
    .file-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      align-items: center;
    }
    .picker {
      position: relative;
      overflow: hidden;
    }
    .picker input {
      position: absolute;
      inset: 0;
      opacity: 0;
      cursor: pointer;
    }
    .hint {
      margin: 0.35rem 0 0;
      font-weight: 400;
    }
    .scan-dialog {
      position: fixed;
      inset: 0;
      z-index: 80;
      display: grid;
      grid-template-rows: 1fr auto;
      background: #050708;
    }
    .preview {
      position: relative;
      min-height: 0;
      background: #000;
    }
    video,
    canvas {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
    canvas {
      pointer-events: none;
    }
    .toolbar {
      display: grid;
      gap: 0.6rem;
      padding: 0.85rem 1rem 1.25rem;
      background: var(--kh-surface);
      border-top: 1px solid var(--kh-border);
    }
    .toolbar p {
      margin: 0;
    }
  `,
})
export class DocumentInput implements OnDestroy {
  readonly fileChange = output<File | null>();
  readonly hint = input(
    'Choose a PDF or photo, or scan a paper with the camera. The scanner finds the page edges and flattens them. Add more pages before you finish.',
  );
  readonly accept = DOCUMENT_ACCEPT;
  readonly scanning = signal(false);
  readonly scanError = signal<string | null>(null);
  readonly selectedName = signal('');
  readonly pages = signal<Blob[]>([]);
  readonly status = signal('Loading scanner…');
  private readonly loadEngine = inject(PAPER_SCAN_ENGINE_LOADER);
  private readonly zone = inject(NgZone);
  private readonly preview = viewChild<ElementRef<HTMLVideoElement>>('preview');
  private readonly overlay = viewChild<ElementRef<HTMLCanvasElement>>('overlay');
  private engine: PaperScanEngine | null = null;
  private stream: MediaStream | null = null;
  private videoEl: HTMLVideoElement | null = null;
  private raf = 0;

  ngOnDestroy(): void {
    this.stopCamera();
  }

  onFile(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0] ?? null;
    this.selectedName.set(file?.name ?? '');
    this.fileChange.emit(file);
  }

  async startScan(): Promise<void> {
    if (!navigator.mediaDevices?.getUserMedia) {
      this.scanError.set('This device cannot open the camera. Choose a file instead.');
      return;
    }
    this.scanError.set(null);
    this.pages.set([]);
    this.status.set('Loading scanner…');
    this.scanning.set(true);
    try {
      this.engine = await this.loadEngine();
      this.status.set('Starting camera…');
      const stream = await navigator.mediaDevices.getUserMedia(DOCUMENT_CAMERA);
      this.stream = stream;
      const video = await this.waitForPreview();
      this.videoEl = video;
      video.srcObject = stream;
      video.playsInline = true;
      video.muted = true;
      await video.play();
      this.status.set('Align the paper in the frame, then capture.');
      this.zone.runOutsideAngular(() => this.loopHighlight());
    } catch (err) {
      this.stopCamera();
      this.scanning.set(false);
      this.scanError.set(cameraMessage(err));
    }
  }

  async capturePage(): Promise<void> {
    const video = this.videoEl ?? this.preview()?.nativeElement;
    const engine = this.engine;
    if (!video || !engine) {
      return;
    }
    try {
      const page = extractOrFallback(engine, captureFrame(video));
      const blob = await canvasToBlob(page);
      this.pages.update((list) => [...list, blob]);
      const count = this.pages().length;
      this.status.set(
        `${count} page${count === 1 ? '' : 's'} scanned. Capture another or use scans.`,
      );
    } catch (err) {
      this.scanError.set(err instanceof Error ? err.message : 'Could not capture that page.');
    }
  }

  async useScans(): Promise<void> {
    if (!this.pages().length) {
      return;
    }
    try {
      const { imagesToPdf } = await import('./pages-to-pdf');
      const file = await imagesToPdf(this.pages(), scanFilename());
      this.selectedName.set(file.name);
      this.fileChange.emit(file);
      this.cancelScan();
    } catch (err) {
      this.scanError.set(
        err instanceof Error ? err.message : 'Could not build a PDF from those scans.',
      );
    }
  }

  cancelScan(): void {
    this.stopCamera();
    this.pages.set([]);
    this.scanning.set(false);
  }

  private async waitForPreview(): Promise<HTMLVideoElement> {
    for (let attempt = 0; attempt < 10; attempt++) {
      const video = this.preview()?.nativeElement;
      if (video) {
        return video;
      }
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    }
    throw new Error('Camera preview is not available.');
  }

  private loopHighlight(): void {
    if (!this.scanning()) {
      return;
    }
    this.drawHighlight();
    this.raf = requestAnimationFrame(() => this.loopHighlight());
  }

  private drawHighlight(): void {
    const video = this.preview()?.nativeElement;
    const overlay = this.overlay()?.nativeElement;
    const engine = this.engine;
    if (!video || !overlay || !engine || video.readyState < 2) {
      return;
    }
    try {
      const highlighted = engine.highlightPaper(captureFrame(video));
      overlay.width = highlighted.width;
      overlay.height = highlighted.height;
      overlay.getContext('2d')?.drawImage(highlighted, 0, 0);
    } catch {
      /* Empty camera frames can throw inside OpenCV. */
    }
  }

  private stopCamera(): void {
    if (this.raf) {
      cancelAnimationFrame(this.raf);
      this.raf = 0;
    }
    this.stream?.getTracks().forEach((track) => {
      track.stop();
    });
    this.stream = null;
    this.engine = null;
    this.videoEl = null;
    const video = this.preview()?.nativeElement;
    if (video) {
      video.srcObject = null;
    }
  }
}

function cameraMessage(err: unknown): string {
  const name = err instanceof DOMException ? err.name : '';
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
    return 'Camera permission was denied. Allow the camera or choose a file instead.';
  }
  if (name === 'NotFoundError' || name === 'OverconstrainedError') {
    return 'No rear camera was found. Choose a file instead.';
  }
  if (err instanceof Error && err.message) {
    return err.message;
  }
  return 'Could not open the camera. Choose a file instead.';
}
