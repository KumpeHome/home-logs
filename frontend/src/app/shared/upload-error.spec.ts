import { uploadErrorMessage } from './upload-error';

describe('uploadErrorMessage', () => {
  it('uses the API detail when storage fails', () => {
    expect(
      uploadErrorMessage({ status: 400, error: { detail: 'Could not store the uploaded file' } }),
    ).toBe('Could not store the uploaded file');
  });

  it('explains oversized PDFs instead of a generic retry message', () => {
    expect(uploadErrorMessage({ status: 413, error: null })).toBe(
      'That PDF is too large. Use a file under 50 MB.',
    );
  });

  it('explains an empty 400 from the proxy instead of a generic retry', () => {
    expect(uploadErrorMessage({ status: 400, error: null })).toBe(
      'The browser could not send this PDF. Refresh and try a smaller file.',
    );
  });

  it('explains a failed local PDF read', () => {
    expect(uploadErrorMessage({ message: 'Maximum call stack size exceeded' })).toBe(
      'Could not read the PDF. Try another file.',
    );
  });
});
