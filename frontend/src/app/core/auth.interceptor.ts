import { HttpInterceptorFn } from '@angular/common/http';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = (() => {
    try {
      return globalThis.sessionStorage?.getItem('homelogs.access_token');
    } catch {
      return null;
    }
  })();
  if (!token) {
    return next(req);
  }
  let headers = req.headers.set('Authorization', `Bearer ${token}`);
  if (req.body instanceof FormData) {
    headers = headers.delete('Content-Type');
  }
  return next(req.clone({ headers }));
};
