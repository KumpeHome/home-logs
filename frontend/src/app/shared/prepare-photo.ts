export const PHOTO_ACCEPT =
  'image/jpeg,image/png,image/gif,image/webp,image/heic,image/heif,.heic,.heif';

const ALLOWED = new Set(['image/jpeg', 'image/png', 'image/gif', 'image/webp']);

export function isHeicPhoto(file: File): boolean {
  const type = file.type.toLowerCase();
  if (
    type === 'image/heic' ||
    type === 'image/heif' ||
    type === 'image/heic-sequence' ||
    type === 'image/heif-sequence'
  ) {
    return true;
  }
  return /\.hei[cf]$/i.test(file.name);
}

function namedPhoto(file: File): File {
  const name = file.name.trim() || 'photo.jpg';
  if (name === file.name) {
    return file;
  }
  return new File([file], name, { type: file.type || 'image/jpeg' });
}

export async function preparePhoto(file: File): Promise<File> {
  if (isHeicPhoto(file)) {
    return heicToJpeg(file);
  }
  if (ALLOWED.has(file.type)) {
    return namedPhoto(file);
  }
  throw new Error('Photos must be JPEG, PNG, GIF, WebP, or HEIC.');
}

async function heicToJpeg(file: File): Promise<File> {
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    throw new Error(
      'This HEIC photo could not be converted. Save it as JPEG or PNG from Photos and try again.',
    );
  }
  try {
    const canvas = document.createElement('canvas');
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    const context = canvas.getContext('2d');
    if (!context) {
      throw new Error('This HEIC photo could not be converted.');
    }
    context.drawImage(bitmap, 0, 0);
    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob(
        (result) =>
          result ? resolve(result) : reject(new Error('This HEIC photo could not be converted.')),
        'image/jpeg',
        0.92,
      );
    });
    const stem = file.name.replace(/\.hei[cf]$/i, '') || 'photo';
    return new File([blob], `${stem}.jpg`, { type: 'image/jpeg' });
  } finally {
    bitmap.close();
  }
}
