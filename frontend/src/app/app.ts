import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from './core/auth.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  readonly auth = inject(AuthService);

  readonly allNav = [
    { path: '/', label: 'Dashboard', resource: 'tab.dashboard' },
    { path: '/people', label: 'People', resource: 'tab.people' },
    { path: '/logs', label: 'Logs', resource: 'tab.logs' },
    { path: '/forms', label: 'Forms', resource: 'tab.forms' },
    { path: '/school', label: 'School', resource: 'tab.school' },
    { path: '/discipline', label: 'Discipline', resource: 'tab.discipline' },
    { path: '/documents', label: 'Documents', resource: 'tab.documents' },
    { path: '/export', label: 'Export', resource: 'tab.export' },
    { path: '/settings', label: 'Settings', resource: 'tab.settings' },
    { path: '/audit', label: 'Audit', resource: 'tab.audit' },
  ];

  nav(): { path: string; label: string }[] {
    return this.allNav.filter((item) => this.auth.can(item.resource, 'view'));
  }
}
