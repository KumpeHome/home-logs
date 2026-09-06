import { PHOTO_ACCEPT, preparePhoto } from './prepare-photo';

describe('preparePhoto', () => {
  it('accepts HEIC in the file picker list', () => {
    expect(PHOTO_ACCEPT).toContain('image/heic');
    expect(PHOTO_ACCEPT).toContain('.heic');
  });

  it('passes JPEG, PNG, GIF, and WebP through', async () => {
    const png = new File(['png'], 'bruise.png', { type: 'image/png' });
    const prepared = await preparePhoto(png);
    expect(prepared).toBe(png);
  });

  it('rejects unsupported types before upload', async () => {
    const pdf = new File(['%PDF'], 'scan.pdf', { type: 'application/pdf' });
    await expect(preparePhoto(pdf)).rejects.toThrow(/JPEG, PNG, GIF, WebP, or HEIC/i);
  });

  it('converts HEIC to JPEG', async () => {
    const original = globalThis.createImageBitmap;
    const heic = new File(['heic'], 'IMG_1234.HEIC', { type: 'image/heic' });
    Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
      configurable: true,
      value: () => ({ drawImage: () => undefined }),
    });
    Object.defineProperty(HTMLCanvasElement.prototype, 'toBlob', {
      configurable: true,
      value: (callback: BlobCallback) => {
        callback(new Blob(['jpeg'], { type: 'image/jpeg' }));
      },
    });
    globalThis.createImageBitmap = (async () => ({
      width: 2,
      height: 2,
      close: () => undefined,
    })) as typeof createImageBitmap;
    try {
      const prepared = await preparePhoto(heic);
      expect(prepared.type).toBe('image/jpeg');
      expect(prepared.name).toBe('IMG_1234.jpg');
    } finally {
      globalThis.createImageBitmap = original;
    }
  });

  it('explains when a HEIC photo cannot be decoded', async () => {
    const original = globalThis.createImageBitmap;
    globalThis.createImageBitmap = (async () => {
      throw new Error('could not decode');
    }) as typeof createImageBitmap;
    try {
      const heic = new File(['heic'], 'photo.heic', { type: 'image/heic' });
      await expect(preparePhoto(heic)).rejects.toThrow(/HEIC/i);
    } finally {
      globalThis.createImageBitmap = original;
    }
  });
});
