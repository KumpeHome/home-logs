export function uploadErrorMessage(err: {
  status?: number;
  error?: unknown;
  message?: string;
}): string {
  const body = err.error;
  if (typeof body === 'string' && body.trim() && body !== 'Internal Server Error') {
    return body;
  }
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
  }
  if (err.status === 413) {
    return 'That PDF is too large. Use a file under 50 MB.';
  }
  if (err.status === 400) {
    return 'The browser could not send this PDF. Refresh and try a smaller file.';
  }
  if (!err.status && err.message) {
    return 'Could not read the PDF. Try another file.';
  }
  return 'Upload failed. Try a smaller PDF or refresh and retry.';
}
