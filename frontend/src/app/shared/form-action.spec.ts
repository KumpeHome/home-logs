import { Subject } from 'rxjs';
import { FormAction, formErrorMessage } from './form-action';

describe('FormAction', () => {
  it('marks busy until the request finishes, then records success', () => {
    const action = new FormAction();
    const request = new Subject<string>();
    let received = '';
    action.run(request, 'Saved.', (value) => {
      received = value;
    });
    expect(action.busy()).toBe(true);
    expect(action.success()).toBeNull();
    request.next('ok');
    request.complete();
    expect(action.busy()).toBe(false);
    expect(action.success()).toBe('Saved.');
    expect(action.error()).toBeNull();
    expect(received).toBe('ok');
  });

  it('records an error and clears busy when the request fails', () => {
    const action = new FormAction();
    const request = new Subject<void>();
    action.run(request, 'Saved.');
    request.error({ error: { detail: 'Nope' } });
    expect(action.busy()).toBe(false);
    expect(action.error()).toBe('Nope');
    expect(action.success()).toBeNull();
  });

  it('reads API detail messages', () => {
    expect(formErrorMessage({ error: { detail: 'Pick a member' } })).toBe('Pick a member');
    expect(formErrorMessage({})).toBe('Could not save. Try again.');
  });
});
