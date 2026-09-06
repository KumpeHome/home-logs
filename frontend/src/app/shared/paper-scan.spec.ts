import {
  DOCUMENT_CAMERA,
  LETTER_HEIGHT,
  LETTER_WIDTH,
  extractOrFallback,
  loadScript,
} from './paper-scan';

describe('paper scan', () => {
  it('asks the browser for the rear camera like a document scanner', () => {
    const video = DOCUMENT_CAMERA.video as MediaTrackConstraints;
    expect(video.facingMode).toEqual({ ideal: 'environment' });
    expect(DOCUMENT_CAMERA.audio).toBe(false);
  });

  it('extracts a letter-size page when the scanner finds paper', () => {
    const frame = document.createElement('canvas');
    frame.width = 640;
    frame.height = 480;
    const extracted = document.createElement('canvas');
    extracted.width = LETTER_WIDTH;
    extracted.height = LETTER_HEIGHT;
    const page = extractOrFallback(
      {
        extractPaper: (image: CanvasImageSource, width: number, height: number) => {
          expect(image).toBe(frame);
          expect(width).toBe(LETTER_WIDTH);
          expect(height).toBe(LETTER_HEIGHT);
          return extracted;
        },
        highlightPaper: () => frame,
      },
      frame,
    );
    expect(page).toBe(extracted);
  });

  it('keeps the full camera frame when no paper edge is found', () => {
    const frame = document.createElement('canvas');
    const page = extractOrFallback(
      {
        extractPaper: () => null,
        highlightPaper: () => frame,
      },
      frame,
    );
    expect(page).toBe(frame);
  });
});

describe('loadScript', () => {
  afterEach(() => {
    document.querySelectorAll('script[src^="/vendor/test-scan-"]').forEach((node) => node.remove());
  });

  it('shares one in-flight load so a second scanner waits for the same script', async () => {
    const src = `/vendor/test-scan-shared-${crypto.randomUUID()}.js`;
    const first = loadScript(src);
    const second = loadScript(src);
    expect(document.querySelectorAll(`script[src="${src}"]`).length).toBe(1);
    let secondSettled = false;
    void second.then(() => {
      secondSettled = true;
    });
    await Promise.resolve();
    expect(secondSettled).toBe(false);
    document.querySelector(`script[src="${src}"]`)?.dispatchEvent(new Event('load'));
    await Promise.all([first, second]);
    expect(secondSettled).toBe(true);
  });
});
