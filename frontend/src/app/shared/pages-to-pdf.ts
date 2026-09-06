import { PDFDocument } from '@cantoo/pdf-lib';

function isPng(bytes: Uint8Array): boolean {
  return (
    bytes.length >= 4 &&
    bytes[0] === 0x89 &&
    bytes[1] === 0x50 &&
    bytes[2] === 0x4e &&
    bytes[3] === 0x47
  );
}

export async function imagesToPdf(pages: Blob[], filename: string): Promise<File> {
  if (!pages.length) {
    throw new Error('Scan at least one page.');
  }
  const pdf = await PDFDocument.create();
  for (const page of pages) {
    const bytes = new Uint8Array(await page.arrayBuffer());
    const image = isPng(bytes) ? await pdf.embedPng(bytes) : await pdf.embedJpg(bytes);
    const pdfPage = pdf.addPage([image.width, image.height]);
    pdfPage.drawImage(image, { x: 0, y: 0, width: image.width, height: image.height });
  }
  const saved = await pdf.save();
  return new File([saved as BlobPart], filename, { type: 'application/pdf' });
}
