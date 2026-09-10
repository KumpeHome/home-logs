import { HttpErrorResponse, type HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, EMPTY, throwError } from 'rxjs';
import { AuthService } from './auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const token = auth.token();
  let outgoing = req;
  if (token) {
    let headers = req.headers.set('Authorization', `Bearer ${token}`);
    if (req.body instanceof FormData) {
      headers = headers.delete('Content-Type');
    }
    outgoing = req.clone({ headers });
  }
  return next(outgoing).pipe(
    catchError((error: unknown) => {
      if (
        error instanceof HttpErrorResponse &&
        error.status === 401 &&
        token &&
        auth.token() === token
      ) {
        auth.logout();
        return EMPTY;
      }
      return throwError(() => error);
    }),
  );
};
