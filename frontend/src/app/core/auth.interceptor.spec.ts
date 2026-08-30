import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { authInterceptor } from './auth.interceptor';

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    sessionStorage.setItem('homelogs.access_token', 'dev-bypass');
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    sessionStorage.clear();
  });

  it('keeps FormData uploads as multipart instead of JSON', () => {
    const form = new FormData();
    form.append('name', 'Agency visit');
    form.append('form_type_code', 'case_worker_visit');
    form.append('file', new Blob(['%PDF-1.4'], { type: 'application/pdf' }), 'visit.pdf');
    http.post('/api/households/h1/documents', form).subscribe();
    const req = httpMock.expectOne('/api/households/h1/documents');
    expect(req.request.body).toBeInstanceOf(FormData);
    const contentType = req.request.headers.get('Content-Type');
    expect(contentType).toBeNull();
    expect(req.request.headers.get('Authorization')).toBe('Bearer dev-bypass');
    req.flush({ id: 't1' });
  });
});
