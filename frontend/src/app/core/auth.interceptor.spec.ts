import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { NavigationEnd, provideRouter, Router } from '@angular/router';
import { filter, firstValueFrom, take } from 'rxjs';
import { ApiService } from './api.service';
import { authInterceptor } from './auth.interceptor';
import { AuthService } from './auth.service';

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let auth: AuthService;
  let router: Router;

  beforeEach(() => {
    sessionStorage.setItem('homelogs.access_token', 'dev-bypass');
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        provideRouter([{ path: 'login', children: [] }]),
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
    router = TestBed.inject(Router);
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

  it('signs out and sends the user to login when the session has expired', async () => {
    auth.me.set({
      subject: 'sam',
      email: 'sam@example.com',
      name: 'Sam',
      scopes: [],
      linked: true,
      pending_memberships: [],
      households: [],
    });
    let failed = false;
    const redirected = firstValueFrom(
      router.events.pipe(
        filter(
          (event): event is NavigationEnd =>
            event instanceof NavigationEnd && event.urlAfterRedirects === '/login',
        ),
        take(1),
      ),
    );
    http.get('/api/households/h1/dashboard').subscribe({
      error: () => {
        failed = true;
      },
    });
    const req = httpMock.expectOne('/api/households/h1/dashboard');
    req.flush(
      { detail: 'Signature has expired' },
      { status: 401, statusText: 'Unauthorized' },
    );
    await redirected;
    expect(failed).toBe(false);
    expect(auth.token()).toBeNull();
    expect(auth.me()).toBeNull();
    expect(sessionStorage.getItem('homelogs.access_token')).toBeNull();
    expect(router.url).toBe('/login');
  });

  it('leaves the session in place when the API returns a non-auth error', () => {
    http.get('/api/households/h1/dashboard').subscribe({
      error: () => undefined,
    });
    const req = httpMock.expectOne('/api/households/h1/dashboard');
    req.flush({ detail: 'boom' }, { status: 500, statusText: 'Server Error' });
    expect(auth.token()).toBe('dev-bypass');
    expect(sessionStorage.getItem('homelogs.access_token')).toBe('dev-bypass');
    expect(router.url).not.toBe('/login');
  });

  it('does not sign out if the access token was replaced before a delayed 401 arrives', () => {
    let failed = false;
    http.get('/api/households/h1/dashboard').subscribe({
      error: () => {
        failed = true;
      },
    });
    const req = httpMock.expectOne('/api/households/h1/dashboard');
    auth.token.set('fresh-token');
    sessionStorage.setItem('homelogs.access_token', 'fresh-token');
    req.flush(
      { detail: 'Signature has expired' },
      { status: 401, statusText: 'Unauthorized' },
    );
    expect(failed).toBe(true);
    expect(auth.token()).toBe('fresh-token');
    expect(sessionStorage.getItem('homelogs.access_token')).toBe('fresh-token');
    expect(router.url).not.toBe('/login');
  });

  it('signs out when an ApiService upload receives 401', async () => {
    const api = TestBed.inject(ApiService);
    const redirected = firstValueFrom(
      router.events.pipe(
        filter(
          (event): event is NavigationEnd =>
            event instanceof NavigationEnd && event.urlAfterRedirects === '/login',
        ),
        take(1),
      ),
    );
    const form = new FormData();
    form.append('file', new File(['png'], 'bruise.png', { type: 'image/png' }));
    let failed = false;
    api.upload('/households/h1/logs/log-9/attachments', form).subscribe({
      error: () => {
        failed = true;
      },
    });
    const req = httpMock.expectOne('/api/households/h1/logs/log-9/attachments');
    expect(req.request.body).toBeInstanceOf(FormData);
    req.flush(
      { detail: 'Signature has expired' },
      { status: 401, statusText: 'Unauthorized' },
    );
    await redirected;
    expect(failed).toBe(false);
    expect(auth.token()).toBeNull();
    expect(router.url).toBe('/login');
  });

  it('signs out when an ApiService file upload receives 401', async () => {
    const api = TestBed.inject(ApiService);
    const redirected = firstValueFrom(
      router.events.pipe(
        filter(
          (event): event is NavigationEnd =>
            event instanceof NavigationEnd && event.urlAfterRedirects === '/login',
        ),
        take(1),
      ),
    );
    const file = new Blob(['%PDF-1.4'], { type: 'application/pdf' });
    api.uploadFile('/households/h1/members/m1/photo', file).subscribe({
      error: () => undefined,
    });
    const req = httpMock.expectOne('/api/households/h1/members/m1/photo');
    expect(req.request.body).toBe(file);
    expect(req.request.headers.get('Content-Type')).toBe('application/pdf');
    req.flush(
      { detail: 'Signature has expired' },
      { status: 401, statusText: 'Unauthorized' },
    );
    await redirected;
    expect(auth.token()).toBeNull();
    expect(router.url).toBe('/login');
  });
});
