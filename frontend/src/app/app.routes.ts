import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';
import { LoginPage } from './features/login';
import { CallbackPage } from './features/callback';
import { PendingPage } from './features/pending';
import { DashboardPage } from './features/dashboard/dashboard';
import { PeoplePage } from './features/people/people';
import { ProfilePage } from './features/people/profile';
import { LogsPage } from './features/logs/logs';
import { FormsArchivePage } from './features/forms/archive';
import { FormViewPage } from './features/forms/view';
import { SchoolPage } from './features/school/school';
import { DisciplinePage } from './features/discipline/discipline';
import { DocumentsPage } from './features/documents/documents';
import { ExportPage } from './features/export/export';
import { SettingsPage } from './features/settings/settings';
import { AuditPage } from './features/audit/audit';

export const routes: Routes = [
  { path: 'login', component: LoginPage },
  { path: 'callback', component: CallbackPage },
  { path: 'pending', component: PendingPage, canActivate: [authGuard] },
  { path: '', canActivate: [authGuard], children: [
    { path: '', component: DashboardPage },
    { path: 'people', component: PeoplePage },
    { path: 'people/:id', component: ProfilePage },
    { path: 'logs', component: LogsPage },
    { path: 'forms', component: FormsArchivePage },
    { path: 'forms/:id', component: FormViewPage },
    { path: 'school', component: SchoolPage },
    { path: 'discipline', component: DisciplinePage },
    { path: 'documents', component: DocumentsPage },
    { path: 'export', component: ExportPage },
    { path: 'settings', component: SettingsPage },
    { path: 'audit', component: AuditPage },
  ]},
];
