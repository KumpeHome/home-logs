import { imagesToPdf } from './pages-to-pdf';

/** 1×1 PNG so pdf-lib can embed a real image without a canvas. */
const PNG_1X1 = Uint8Array.from(
  atob(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  ),
  (ch) => ch.charCodeAt(0),
);

describe('imagesToPdf', () => {
  it('builds a PDF file from scanned page images', async () => {
    const file = await imagesToPdf([new Blob([PNG_1X1], { type: 'image/png' })], 'scan.pdf');
    expect(file.type).toBe('application/pdf');
    expect(file.name).toBe('scan.pdf');
    const header = new TextDecoder('latin1').decode(await file.slice(0, 5).arrayBuffer());
    expect(header).toBe('%PDF-');
  });

  it('adds one PDF page per scanned image', async () => {
    const file = await imagesToPdf(
      [new Blob([PNG_1X1], { type: 'image/png' }), new Blob([PNG_1X1], { type: 'image/png' })],
      'pages.pdf',
    );
    const text = new TextDecoder('latin1').decode(await file.arrayBuffer());
    const pageObjects = text.match(/\/Type\s*\/Page(?!s)/g) ?? [];
    expect(pageObjects.length).toBe(2);
  });
});
