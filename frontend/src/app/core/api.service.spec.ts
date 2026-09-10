import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { firstValueFrom } from 'rxjs';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';

describe('ApiService.upload', () => {
  let api: ApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { token: () => 'dev-bypass', householdId: () => 'h1' } },
      ],
    });
    api = TestBed.inject(ApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('sends the PDF bytes with an application/pdf Content-Type instead of multipart', async () => {
    const file = new Blob(['%PDF-1.4'], { type: 'application/pdf' });
    const pending = firstValueFrom(api.uploadFile('/households/h1/members/m1/photo', file));
    const req = httpMock.expectOne('/api/households/h1/members/m1/photo');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toBe(file);
    expect(req.request.headers.get('Content-Type')).toBe('application/pdf');
    req.flush({ id: 't1' }, { status: 201, statusText: 'Created' });
    expect(await pending).toEqual({ id: 't1' });
  });

  it('posts FormData without Content-Type so the browser can add the boundary', async () => {
    const form = new FormData();
    form.append('file', new File(['png'], 'bruise.png', { type: 'image/png' }));
    const pending = firstValueFrom(api.upload('/households/h1/logs/log-9/attachments', form));
    const req = httpMock.expectOne('/api/households/h1/logs/log-9/attachments');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toBe(form);
    expect(req.request.headers.get('Content-Type')).toBeNull();
    req.flush({ id: 'a1' });
    expect(await pending).toEqual({ id: 'a1' });
  });
});
