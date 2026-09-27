import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { FormAction, formErrorMessage } from '../../shared/form-action';
import { FormStatus } from '../../shared/form-status';

type NotificationSubject = { id: string | null; name: string; kind: 'member' | 'household' };
type NotificationTopic = {
  code: string;
  name: string;
  description: string;
  applies_to: 'member' | 'any';
};
type SubscriptionChoice = { topic: string; subject_member_id: string | null };
type ConfigurableMember = { id: string; name: string; household_role: string };

type NotificationSettings = {
  member_id: string;
  member_name: string;
  household_role: string;
  email: string | null;
  email_enabled: boolean;
  pushover_enabled: boolean;
  pushover_connected: boolean;
  pushover_key_source: 'subscription' | 'user_key' | null;
  pushover_subscription_available: boolean;
  dose_lead_minutes: number;
  dose_window_before_minutes: number;
  dose_window_after_minutes: number;
  dose_repeat_count: number;
  dose_repeat_interval_minutes: number;
  subscriptions: SubscriptionChoice[];
  subjects: NotificationSubject[];
  topics: NotificationTopic[];
  configurable_members: ConfigurableMember[];
};

@Component({
  selector: 'hl-notifications',
  imports: [FormsModule, FormStatus],
  template: `
    <header class="page-head">
      <div>
        <p class="eyebrow">Account</p>
        <h1>Notifications</h1>
        <p class="lede">
          Choose email, Pushover, or both. Kids can set their own reminders, and parents can set
          them for a child.
        </p>
      </div>
    </header>
    @if (settings(); as current) {
      <form class="hl-card hl-form" (ngSubmit)="save()">
        @if (current.configurable_members.length > 1) {
          <label>
            Whose notifications
            <select
              data-test="notification-member"
              [value]="current.member_id"
              (change)="selectMember($any($event.target).value)"
              name="member"
            >
              @for (member of current.configurable_members; track member.id) {
                <option [value]="member.id">{{ member.name }}</option>
              }
            </select>
          </label>
        }

        <section class="block">
          <h2>How you get notified</h2>
          <label class="check">
            <input
              type="checkbox"
              [(ngModel)]="emailEnabled"
              name="emailOn"
              data-test="email-enabled"
            />
            <span>
              Email
              @if (current.email) {
                <span class="muted">{{ current.email }}</span>
              } @else {
                <span class="muted">No email on this profile</span>
              }
            </span>
          </label>
          <label class="check">
            <input
              type="checkbox"
              [(ngModel)]="pushoverEnabled"
              name="pushoverOn"
              data-test="pushover-enabled"
            />
            <span>Pushover</span>
          </label>
          @if (current.pushover_connected) {
            <p data-test="pushover-status">
              @if (current.pushover_key_source === 'user_key') {
                Connected with a Pushover user key.
              } @else {
                Connected with a Pushover subscription.
              }
            </p>
            <button class="hl-btn secondary" type="button" (click)="disconnectPushover()">
              Disconnect Pushover
            </button>
          }
          @if (current.pushover_subscription_available) {
            <a
              class="pushover_button"
              href="https://pushover.net/"
              data-test="subscribe-pushover"
              (click)="subscribe($event)"
            >
              Subscribe With Pushover
            </a>
          }
          <label>
            Pushover user key
            <input
              [(ngModel)]="userKey"
              name="pushoverKey"
              data-test="pushover-user-key"
              autocomplete="off"
              placeholder="Optional if you subscribe instead"
            />
          </label>
        </section>

        <section class="block">
          <h2>{{ reminderHeading(current) }}</h2>
          @if (showsChildHint(current)) {
            <p class="hint">
              Each person is separate. You can be notified about one child and not another.
            </p>
          }
          @for (subject of current.subjects; track subject.id ?? 'household') {
            <div class="reminder-row">
              <span class="reminder-who" data-test="reminder-who">{{ subject.name }}</span>
              <div class="reminder-options">
                @for (topic of topicsFor(current, subject.kind); track topic.code) {
                  <label class="check">
                    <input
                      type="checkbox"
                      [attr.data-test]="subTest(topic.code, subject.id)"
                      [checked]="checked(topic.code, subject.id)"
                      (change)="toggle(topic.code, subject.id, $any($event.target).checked)"
                    />
                    <span>{{ topic.name }}</span>
                  </label>
                }
              </div>
            </div>
          }
        </section>

        <section class="block">
          <h2>When a dose is due</h2>
          <div class="timing">
            <label>
              Minutes before it is due
              <input
                type="number"
                min="0"
                max="180"
                [(ngModel)]="doseLead"
                name="lead"
                data-test="dose-lead"
              />
            </label>
            <label>
              Minutes before that count as given
              <input
                type="number"
                min="0"
                max="240"
                [(ngModel)]="windowBefore"
                name="windowBefore"
                data-test="dose-window-before"
              />
            </label>
            <label>
              Minutes after that count as given
              <input
                type="number"
                min="0"
                max="240"
                [(ngModel)]="windowAfter"
                name="windowAfter"
                data-test="dose-window-after"
              />
            </label>
            <label>
              Times to remind if it is not logged
              <input
                type="number"
                min="1"
                max="10"
                [(ngModel)]="repeatCount"
                name="repeatCount"
                data-test="dose-repeat-count"
              />
            </label>
            <label>
              Minutes between reminders
              <input
                type="number"
                min="1"
                max="180"
                [(ngModel)]="repeatInterval"
                name="repeatInterval"
                data-test="dose-repeat-interval"
              />
            </label>
          </div>
          <p class="hint">
            Any submitted log for that dose inside the window stops reminders, including given,
            refused, missed, and held.
          </p>
        </section>

        <div class="actions">
          <button class="hl-btn" data-test="save-notifications" [disabled]="action.busy()">
            {{ action.busy() ? 'Saving…' : 'Save notifications' }}
          </button>
          <button
            class="hl-btn secondary"
            type="button"
            data-test="send-test"
            [disabled]="testAction.busy()"
            (click)="sendTest()"
          >
            {{ testAction.busy() ? 'Sending…' : 'Send test' }}
          </button>
        </div>
        <hl-form-status
          [busy]="action.busy()"
          [success]="action.success()"
          [error]="action.error()"
        />
        <hl-form-status
          [busy]="testAction.busy()"
          [success]="testAction.success()"
          [error]="testAction.error()"
          busyLabel="Sending…"
        />
      </form>
    }
  `,
  styles: `
    h2 {
      margin: 0;
      font-size: 1rem;
    }

    .block {
      display: grid;
      gap: 0.75rem;
    }

    .hint {
      margin: 0;
      color: var(--kh-muted, #5c6570);
    }

    label.check {
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: 0.55rem;
      min-height: 0;
      font-weight: 500;
    }

    label.check input[type='checkbox'] {
      width: 1.05rem;
      height: 1.05rem;
      min-height: 0;
      margin: 0;
      padding: 0;
      accent-color: var(--kh-primary, #1d4e89);
    }

    .reminder-row {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 0.65rem 1.25rem;
      padding: 0.7rem 0.9rem;
      border: 1px solid var(--kh-border, #d7dde5);
      border-radius: 0.7rem;
      background: var(--kh-surface-2, #f7f8fa);
    }

    .reminder-who {
      font-weight: 650;
      min-width: 8rem;
    }

    .reminder-options {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem 1.25rem;
    }

    .timing {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
      gap: 0.75rem;
    }

    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      align-items: center;
    }

    a.pushover_button {
      box-sizing: border-box !important;
      justify-self: start;
      width: fit-content !important;
      background-color: #eee !important;
      background: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAycHgiIGhlaWdodD0iNjAycHgiIHZlcnNpb249IjEuMSIgdmlld0JveD0iNTcgNTcgNjAyIDYwMiIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSg1OC45NjQgNTguODg4KSIgb3BhY2l0eT0iLjkxIj48ZWxsaXBzZSB0cmFuc2Zvcm09Im1hdHJpeCgtLjY3NDU3IC43MzgyMSAtLjczODIxIC0uNjc0NTcgNTU2LjgzIDI0MS42MSkiIGN4PSIyMTYuMzEiIGN5PSIxNTIuMDgiIHJ4PSIyOTYuODYiIHJ5PSIyOTYuODYiIGZpbGw9IiMyNDlkZjEiIGZpbGwtcnVsZT0iZXZlbm9kZCIgc3Ryb2tlLXdpZHRoPSIwIi8+PHBhdGggZD0ibTI4MC45NSAxNzIuNTFsNzQuNDgtOS44LTcyLjUyIDE2My42NmMxMi43NC0wLjk4IDI1LjIzMy01LjMwNyAzNy40OC0xMi45OCAxMi4yNTMtNy42OCAyMy41MjctMTcuMzE3IDMzLjgyLTI4LjkxIDEwLjI4Ny0xMS42IDE5LjE4Ny0yNC41MDMgMjYuNy0zOC43MSA3LjUxMy0xNC4yMTMgMTIuOTAzLTI4LjE4IDE2LjE3LTQxLjkgMS45Ni04LjQ5MyAyLjg2LTE2LjY2IDIuNy0yNC41LTAuMTY3LTcuODQtMi4yMS0xNC43LTYuMTMtMjAuNThzLTkuODgzLTEwLjYxNy0xNy44OS0xNC4yMWMtOC0zLjU5My0xOC44Ni01LjM5LTMyLjU4LTUuMzktMTYuMDA3IDAtMzEuNzcgMi42MTMtNDcuMjkgNy44NC0xNS41MTMgNS4yMjctMjkuODg3IDEyLjgyMy00My4xMiAyMi43OS0xMy4yMjcgOS45Ni0yNC43NCAyMi4zNzMtMzQuNTQgMzcuMjQtOS44IDE0Ljg2LTE2LjgyMyAzMS43NjMtMjEuMDcgNTAuNzEtMS42MzMgNi4yMDctMi42MTMgMTEuMTg3LTIuOTQgMTQuOTQtMC4zMjcgMy43Ni0wLjQwNyA2Ljg2My0wLjI0IDkuMzEgMC4xNiAyLjQ1MyAwLjQ4MyA0LjMzMyAwLjk3IDUuNjQgMC40OTMgMS4zMDcgMC45MDMgMi42MTMgMS4yMyAzLjkyLTE2LjY2IDAtMjguODMtMy4zNS0zNi41MS0xMC4wNS03LjY3My02LjY5My05LjU1LTE4LjM3LTUuNjMtMzUuMDMgMy45Mi0xNy4zMTMgMTIuODIzLTMzLjgxIDI2LjcxLTQ5LjQ5IDEzLjg4LTE1LjY4IDMwLjM3My0yOS40ODMgNDkuNDgtNDEuNDEgMTkuMTEzLTExLjkyIDQwLjAyLTIxLjM5IDYyLjcyLTI4LjQxIDIyLjcwNy03LjAyNyA0NC44NC0xMC41NCA2Ni40LTEwLjU0IDE4Ljk0NyAwIDM0Ljg3IDIuNjkzIDQ3Ljc3IDguMDggMTIuOTA3IDUuMzkzIDIyLjk1MyAxMi41IDMwLjE0IDIxLjMyczExLjY3NyAxOS4xMSAxMy40NyAzMC44N2MxLjggMTEuNzYgMS4yMyAyNC4wMS0xLjcxIDM2Ljc1LTMuNTkzIDE1LjM1My0xMC4zNzMgMzAuNzktMjAuMzQgNDYuMzEtOS45NiAxNS41MTMtMjIuNDUzIDI5LjU2LTM3LjQ4IDQyLjE0LTE1LjAyNyAxMi41NzMtMzIuMjYgMjIuNzgtNTEuNyAzMC42Mi0xOS40MzMgNy44NC00MC4wOTMgMTEuNzYtNjEuOTggMTEuNzZoLTIuNDVsLTYyLjIzIDEzOS42NWgtNzAuNTZsMTM4LjY3LTMxMS42NHoiIGZpbGw9IiNmZmYiIHN0eWxlPSJ3aGl0ZS1zcGFjZTpwcmUiLz48L2c+PC9zdmc+)
        3px 3px no-repeat;
      background-size: 15px 15px;
      border-bottom: 2px solid rgba(22, 22, 22, 0.25) !important;
      border-right: 2px solid rgba(22, 22, 22, 0.25) !important;
      box-shadow:
        0 2px 0 rgba(255, 255, 255, 0.2) inset,
        0 2px 0 rgba(0, 0, 0, 0.05) !important;
      border-radius: 3px !important;
      color: #333 !important;
      display: inline-block !important;
      font:
        bold 11px/18px 'Helvetica Neue',
        Arial,
        sans-serif !important;
      cursor: pointer !important;
      height: 22px !important;
      padding: 1px 6px 20px 22px !important;
      overflow: hidden !important;
      text-decoration: none !important;
      vertical-align: middle !important;
    }
  `,
})
export class NotificationsPage {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly settings = signal<NotificationSettings | null>(null);
  readonly action = new FormAction();
  readonly testAction = new FormAction();
  emailEnabled = false;
  pushoverEnabled = false;
  doseLead = 15;
  windowBefore = 30;
  windowAfter = 60;
  repeatCount = 1;
  repeatInterval = 15;
  userKey = '';
  private subscriptions: SubscriptionChoice[] = [];
  private clearPushoverKey = false;

  constructor() {
    const params = this.route.snapshot.queryParamMap;
    const member = params.get('member');
    const rand = params.get('rand');
    if (rand) {
      this.completeSubscription(
        member,
        rand,
        params.get('pushover_user_key'),
        params.get('pushover_unsubscribed') === '1',
      );
      return;
    }
    if (params.get('pushover_failed') === '1') {
      this.action.fail('Pushover subscription was canceled.');
    }
    this.load(member);
  }

  selectMember(memberId: string): void {
    this.userKey = '';
    this.clearPushoverKey = false;
    this.load(memberId);
  }

  reminderHeading(current: NotificationSettings): string {
    if (current.household_role === 'child' && current.configurable_members.length > 1) {
      return `Reminders ${current.member_name} receives`;
    }
    return current.subjects.length > 1 ? 'Notify me about' : 'Reminders';
  }

  showsChildHint(current: NotificationSettings): boolean {
    return (
      current.household_role !== 'child' &&
      current.subjects.filter((subject) => subject.kind === 'member').length > 1
    );
  }

  topicsFor(current: NotificationSettings, kind: string): NotificationTopic[] {
    if (kind === 'household') {
      return current.topics.filter((topic) => topic.applies_to === 'any');
    }
    return current.topics;
  }

  checked(topic: string, subjectId: string | null): boolean {
    return this.subscriptions.some(
      (item) => item.topic === topic && item.subject_member_id === subjectId,
    );
  }

  toggle(topic: string, subjectId: string | null, on: boolean): void {
    this.subscriptions = this.subscriptions.filter(
      (item) => !(item.topic === topic && item.subject_member_id === subjectId),
    );
    if (on) {
      this.subscriptions = [...this.subscriptions, { topic, subject_member_id: subjectId }];
    }
  }

  subTest(topic: string, subjectId: string | null): string {
    return `sub-${topic}-${subjectId ?? 'household'}`;
  }

  subscribe(event?: Event): void {
    event?.preventDefault();
    const memberId = this.settings()?.member_id;
    if (!memberId) {
      return;
    }
    this.api
      .post<{ subscribe_url: string }>(
        `/households/${this.api.hid()}/notifications/pushover/start`,
        { member_id: memberId },
      )
      .subscribe({
        next: (row) => this.openUrl(row.subscribe_url),
        error: (err) => this.action.fail(formErrorMessage(err, 'Could not start Pushover.')),
      });
  }

  openUrl(url: string): void {
    globalThis.location.assign(url);
  }

  disconnectPushover(): void {
    this.pushoverEnabled = false;
    this.userKey = '';
    this.clearPushoverKey = true;
    this.save();
  }

  save(): void {
    const current = this.settings();
    if (!current) {
      return;
    }
    const typedKey = this.userKey.trim();
    this.action.run(
      this.api.put<NotificationSettings>(`/households/${this.api.hid()}/notifications`, {
        member_id: current.member_id,
        email_enabled: this.emailEnabled,
        pushover_enabled: this.pushoverEnabled,
        pushover_user_key: this.clearPushoverKey ? '' : typedKey || null,
        dose_lead_minutes: Number(this.doseLead),
        dose_window_before_minutes: Number(this.windowBefore),
        dose_window_after_minutes: Number(this.windowAfter),
        dose_repeat_count: Number(this.repeatCount),
        dose_repeat_interval_minutes: Number(this.repeatInterval),
        subscriptions: this.subscriptions,
      }),
      'Notifications saved.',
      (row) => {
        this.clearPushoverKey = false;
        this.userKey = '';
        this.apply(row);
      },
    );
  }

  sendTest(): void {
    const current = this.settings();
    if (!current) {
      return;
    }
    this.testAction.begin();
    this.api
      .post<{ deliveries: { channel: string; status: string }[] }>(
        `/households/${this.api.hid()}/notifications/test`,
        { member_id: current.member_id },
      )
      .subscribe({
        next: (row) => this.testAction.succeed(testSummary(row.deliveries)),
        error: (err) => this.testAction.fail(formErrorMessage(err, 'Could not send a test.')),
      });
  }

  private completeSubscription(
    memberId: string | null,
    rand: string,
    userKey: string | null,
    unsubscribed: boolean,
  ): void {
    this.action.begin();
    this.api
      .post<NotificationSettings>(`/households/${this.api.hid()}/notifications/pushover/complete`, {
        member_id: memberId,
        rand,
        pushover_user_key: userKey,
        pushover_unsubscribed: unsubscribed,
      })
      .subscribe({
        next: (row) => {
          this.action.succeed(
            unsubscribed ? 'Pushover disconnected.' : 'Pushover subscription saved.',
          );
          void this.router.navigate(['/notifications'], {
            queryParams: memberId ? { member: memberId } : {},
          });
          this.apply(row);
        },
        error: (err) => {
          this.action.fail(formErrorMessage(err, 'Could not finish the Pushover subscription.'));
          this.load(memberId);
        },
      });
  }

  private load(memberId: string | null): void {
    const query = memberId ? `?member_id=${encodeURIComponent(memberId)}` : '';
    this.api
      .get<NotificationSettings>(`/households/${this.api.hid()}/notifications${query}`)
      .subscribe((row) => this.apply(row));
  }

  private apply(row: NotificationSettings): void {
    this.settings.set(row);
    this.emailEnabled = row.email_enabled;
    this.pushoverEnabled = row.pushover_enabled;
    this.doseLead = row.dose_lead_minutes ?? 15;
    this.windowBefore = row.dose_window_before_minutes ?? 30;
    this.windowAfter = row.dose_window_after_minutes ?? 60;
    this.repeatCount = row.dose_repeat_count ?? 1;
    this.repeatInterval = row.dose_repeat_interval_minutes ?? 15;
    this.subscriptions = row.subscriptions.map((item) => ({ ...item }));
  }
}

function testSummary(deliveries: { channel: string; status: string }[]): string {
  const sent = deliveries
    .filter((item) => item.status === 'sent')
    .map((item) => (item.channel === 'pushover' ? 'Pushover' : 'email'));
  if (sent.length === 0) {
    return 'Test did not send.';
  }
  if (sent.length === 1) {
    return `Test sent by ${sent[0]}.`;
  }
  return `Test sent by ${sent.slice(0, -1).join(', ')} and ${sent.at(-1)}.`;
}
