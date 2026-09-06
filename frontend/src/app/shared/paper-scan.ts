import { InjectionToken } from '@angular/core';

/** US Letter at 150 DPI — typical document-scanner output. */
export const LETTER_WIDTH = 1275;
export const LETTER_HEIGHT = 1650;

export const DOCUMENT_ACCEPT =
  'application/pdf,image/jpeg,image/png,image/webp,image/heic,image/heif,.pdf,.jpg,.jpeg,.png,.webp,.heic,.heif';

export const DOCUMENT_CAMERA: MediaStreamConstraints = {
  audio: false,
  video: {
    facingMode: { ideal: 'environment' },
    width: { ideal: 1920 },
    height: { ideal: 1080 },
  },
};

export const OPENCV_SCRIPT_SRC = 'https://cdn.jsdelivr.net/npm/jscanify@1.4.3/src/opencv.js';
export const JSCANIFY_SCRIPT_SRC = '/vendor/document-scanner/jscanify.js';

export interface PaperScanEngine {
  highlightPaper(image: CanvasImageSource): HTMLCanvasElement;
  extractPaper(image: CanvasImageSource, width: number, height: number): HTMLCanvasElement | null;
}

type JscanifyInstance = {
  highlightPaper(
    image: CanvasImageSource,
    options?: { color?: string; thickness?: number },
  ): HTMLCanvasElement;
  extractPaper(image: CanvasImageSource, width: number, height: number): HTMLCanvasElement | null;
};

type ScannerWindow = Window & {
  cv?: { Mat?: unknown };
  jscanify?: new () => JscanifyInstance;
};

export const PAPER_SCAN_ENGINE_LOADER = new InjectionToken<() => Promise<PaperScanEngine>>(
  'PAPER_SCAN_ENGINE_LOADER',
  { providedIn: 'root', factory: () => loadJscanifyEngine },
);

export function extractOrFallback(
  engine: PaperScanEngine,
  frame: HTMLCanvasElement,
): HTMLCanvasElement {
  return engine.extractPaper(frame, LETTER_WIDTH, LETTER_HEIGHT) ?? frame;
}

export function captureFrame(video: HTMLVideoElement): HTMLCanvasElement {
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth || video.clientWidth || 640;
  canvas.height = video.videoHeight || video.clientHeight || 480;
  canvas.getContext('2d')?.drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas;
}

export function canvasToBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const fail = () => reject(new Error('Could not capture that page.'));
    if (typeof canvas.toBlob !== 'function') {
      fail();
      return;
    }
    canvas.toBlob((blob) => (blob ? resolve(blob) : fail()), 'image/jpeg', 0.88);
  });
}

export function scanFilename(now = new Date()): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `scan-${year}-${month}-${day}.pdf`;
}

export async function loadJscanifyEngine(): Promise<PaperScanEngine> {
  const win = window as ScannerWindow;
  await loadScript(OPENCV_SCRIPT_SRC);
  await waitUntil(() => Boolean(win.cv?.Mat), 20000, 'document scanner');
  await loadScript(JSCANIFY_SCRIPT_SRC);
  const ctor = win.jscanify;
  if (!ctor) {
    throw new Error('Document scanner failed to load. Check your connection and try again.');
  }
  const scanner = new ctor();
  return {
    highlightPaper: (image) => scanner.highlightPaper(image, { color: '#10d9e8', thickness: 6 }),
    extractPaper: (image, width, height) => scanner.extractPaper(image, width, height),
  };
}

const scriptLoads = new Map<string, Promise<void>>();

export function loadScript(src: string): Promise<void> {
  const pending = scriptLoads.get(src);
  if (pending) {
    return pending;
  }
  const existing = document.querySelector<HTMLScriptElement>(`script[src="${src}"]`);
  if (existing?.dataset['loaded'] === 'true') {
    return Promise.resolve();
  }
  const promise = new Promise<void>((resolve, reject) => {
    const script = existing ?? document.createElement('script');
    const succeed = () => {
      script.dataset['loaded'] = 'true';
      resolve();
    };
    const fail = () => {
      scriptLoads.delete(src);
      reject(new Error(`Could not load ${src}`));
    };
    if (existing) {
      existing.addEventListener('load', succeed, { once: true });
      existing.addEventListener('error', fail, { once: true });
      return;
    }
    script.src = src;
    script.async = true;
    script.onload = succeed;
    script.onerror = fail;
    document.head.appendChild(script);
  });
  scriptLoads.set(src, promise);
  return promise;
}

function waitUntil(ready: () => boolean, timeoutMs: number, label: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const started = Date.now();
    const tick = () => {
      if (ready()) {
        resolve();
        return;
      }
      if (Date.now() - started > timeoutMs) {
        reject(new Error(`Timed out loading the ${label}. Try again.`));
        return;
      }
      window.setTimeout(tick, 100);
    };
    tick();
  });
}
