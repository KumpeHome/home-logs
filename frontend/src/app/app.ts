import { Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from './core/auth.service';

type NavItem = { path: string; label: string; resource: string; group: string };

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  readonly auth = inject(AuthService);
  readonly navOpen = signal(false);

  readonly allNav: NavItem[] = [
    { path: '/', label: 'Dashboard', resource: 'tab.dashboard', group: 'Home' },
    { path: '/people', label: 'Members', resource: 'tab.people', group: 'Home' },
    { path: '/logs', label: 'Logs', resource: 'tab.logs', group: 'Care' },
    { path: '/school', label: 'School', resource: 'tab.school', group: 'Care' },
    { path: '/discipline', label: 'Behavior', resource: 'tab.discipline', group: 'Care' },
    { path: '/forms', label: 'Submitted', resource: 'tab.forms', group: 'Records' },
    { path: '/documents', label: 'Documents', resource: 'tab.documents', group: 'Records' },
    { path: '/export', label: 'Reports', resource: 'tab.export', group: 'Records' },
    { path: '/audit', label: 'Activity', resource: 'tab.audit', group: 'Records' },
    { path: '/settings', label: 'Settings', resource: 'tab.settings', group: 'Account' },
  ];

  navGroups(): { name: string; items: { path: string; label: string }[] }[] {
    const names = ['Home', 'Care', 'Records', 'Account'];
    return names
      .map((name) => ({
        name,
        items: this.allNav
          .filter((item) => item.group === name && this.auth.can(item.resource, 'view'))
          .map(({ path, label }) => ({ path, label })),
      }))
      .filter((group) => group.items.length);
  }

  canAddRecord(): boolean {
    return this.auth.can('tab.logs', 'view');
  }

  closeNav(): void {
    this.navOpen.set(false);
  }

  toggleNav(): void {
    this.navOpen.update((open) => !open);
  }
}
