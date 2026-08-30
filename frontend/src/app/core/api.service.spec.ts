import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';

describe('ApiService.upload', () => {
  const originalXhr = globalThis.XMLHttpRequest;

  afterEach(() => {
    globalThis.XMLHttpRequest = originalXhr;
  });

  it('sends the PDF bytes with an application/pdf Content-Type instead of multipart', async () => {
    const headers: string[] = [];
    let sentBody: unknown;
    globalThis.XMLHttpRequest = class {
      status = 201;
      responseText = '{"id":"t1"}';
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      open(): void {}
      setRequestHeader(name: string, value: string): void {
        headers.push(`${name}: ${value}`);
      }
      send(body?: Document | XMLHttpRequestBodyInit | null): void {
        sentBody = body;
        this.onload?.();
      }
      abort(): void {}
    } as unknown as typeof XMLHttpRequest;

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        { provide: AuthService, useValue: { token: () => 'dev-bypass', householdId: () => 'h1' } },
      ],
    });
    const api = TestBed.inject(ApiService);
    const file = new Blob(['%PDF-1.4'], { type: 'application/pdf' });
    const result = await firstValueFrom(
      api.uploadFile('/households/h1/members/m1/photo', file),
    );
    expect(result).toEqual({ id: 't1' });
    expect(sentBody).toBe(file);
    expect(headers).toContain('Content-Type: application/pdf');
    expect(headers).toContain('Authorization: Bearer dev-bypass');
  });
});
