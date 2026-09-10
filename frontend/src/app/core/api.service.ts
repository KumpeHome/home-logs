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
    return this.post<T>(path, form);
  }

  uploadFile<T>(path: string, file: Blob): Observable<T> {
    return this.http.post<T>(`${environment.apiUrl}${path}`, file, {
      headers: { 'Content-Type': file.type || 'application/pdf' },
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
