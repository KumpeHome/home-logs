import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from './environment';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  get<T>(path: string): Observable<T> {
    return this.http.get<T>(`${environment.apiUrl}${path}`);
  }

  post<T>(path: string, body: unknown): Observable<T> {
    return this.http.post<T>(`${environment.apiUrl}${path}`, body);
  }

  put<T>(path: string, body: unknown): Observable<T> {
    return this.http.put<T>(`${environment.apiUrl}${path}`, body);
  }

  patch<T>(path: string, body: unknown): Observable<T> {
    return this.http.patch<T>(`${environment.apiUrl}${path}`, body);
  }

  delete(path: string): Observable<void> {
    return this.http.delete<void>(`${environment.apiUrl}${path}`);
  }

  upload<T>(path: string, form: FormData): Observable<T> {
    return this.sendFile<T>(`${environment.apiUrl}${path}`, form, null);
  }

  uploadFile<T>(path: string, file: Blob): Observable<T> {
    return this.sendFile<T>(
      `${environment.apiUrl}${path}`,
      file,
      file.type || 'application/pdf',
    );
  }

  private sendFile<T>(
    url: string,
    body: Blob | FormData,
    contentType: string | null,
  ): Observable<T> {
    return new Observable((subscriber) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', url);
      const token = this.auth.token();
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }
      if (contentType) {
        xhr.setRequestHeader('Content-Type', contentType);
      }
      xhr.onload = () => {
        let parsed: unknown = null;
        if (xhr.responseText) {
          try {
            parsed = JSON.parse(xhr.responseText) as unknown;
          } catch {
            parsed = xhr.responseText;
          }
        }
        if (xhr.status >= 200 && xhr.status < 300) {
          subscriber.next(parsed as T);
          subscriber.complete();
          return;
        }
        subscriber.error({ status: xhr.status, error: parsed });
      };
      xhr.onerror = () => subscriber.error({ status: 0, error: null });
      xhr.send(body);
      return () => xhr.abort();
    });
  }

  hid(): string {
    return this.auth.householdId() ?? '';
  }

  timezone(): string {
    return this.auth.householdTimezone();
  }

  getBlob(path: string): Observable<Blob> {
    return this.http.get(`${environment.apiUrl}${path}`, { responseType: 'blob' });
  }

  postBlob(path: string, body: unknown): Observable<Blob> {
    return this.http.post(`${environment.apiUrl}${path}`, body, { responseType: 'blob' });
  }
}

