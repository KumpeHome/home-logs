import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { catchError, forkJoin, of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { MemberPhoto } from '../../shared/member-photo';
import { composeDose, DOSE_UNITS, parseDose } from '../../shared/dose';
import { flagLabel, isAdministerable, MEDICATION_FLAGS } from '../../shared/medication';

type Tab = 'overview' | 'health' | 'school' | 'team' | 'records' | 'permissions';
type PermResource = { code: string; name: string; group: string; actions: string[] };

@Component({
  selector: 'hl-profile',
  imports: [FormsModule, MemberPhoto, RouterLink, DatePipe],
  templateUrl: './profile.html',
  styleUrl: './profile.scss',
})
export class ProfilePage {
  readonly api = inject(ApiService);
  readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  readonly catalog = signal<PermResource[]>([]);
  readonly permSet = signal(new Set<string>());
  readonly member = signal<any>(null);
  readonly profile = signal<any>(null);
  readonly logs = signal<any[]>([]);
  readonly enrollments = signal<any[]>([]);
  readonly documents = signal<any[]>([]);
  readonly discipline = signal<any[]>([]);
  readonly tab = signal<Tab>('overview');
  readonly editing = signal(false);
  readonly adding = signal<string | null>(null);
  readonly otcCatalog = signal<any[]>([]);
  readonly medFilter = signal<'active' | 'inactive' | 'all'>('active');
  readonly editingMedId = signal<string | null>(null);
  readonly medFlags = MEDICATION_FLAGS;
  readonly doseUnits = DOSE_UNITS;
  draft: any = {};
  otcId = '';
  medTimes = '08:00';
  med: any = this.emptyMed();
  allergy: any = this.emptyAllergy();
  diagnosis: any = this.emptyDiagnosis();
  disability: any = this.emptyDisability();
  clinician: any = this.emptyClinician();
  pro: any = this.emptyPro();
  emergency: any = this.emptyEmergency();

  constructor() {
    this.reload(this.route.snapshot.paramMap.get('id')!);
  }

  memberId(): string {
    return this.route.snapshot.paramMap.get('id')!;
  }

  timezone(): string {
    return this.api.timezone();
  }

  displayName(): string {
    const member = this.member();
    const profile = this.profile();
    return member?.legal_name || `${profile?.first_name ?? ''} ${profile?.last_name ?? ''}`.trim();
  }

  show(value: unknown): string {
    if (value === null || value === undefined || value === '') {
      return '—';
    }
    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No';
    }
    return String(value);
  }

  startEdit(): void {
    this.draft = {
      ...this.profile(),
      household_role: this.member()?.household_role,
      email: this.member()?.email ?? '',
    };
    this.editing.set(true);
  }

  cancelEdit(): void {
    this.editing.set(false);
  }

  toggleAdd(section: string): void {
    if (section === 'medications') {
      this.editingMedId.set(null);
      this.med = this.emptyMed();
      this.medTimes = '08:00';
    }
    this.adding.update((current) => (current === section ? null : section));
  }

  reload(id: string = this.memberId()): void {
    const hid = this.api.hid();
    const empty = catchError(() => of([] as any[]));
    forkJoin({
      member: this.api.get<any>(`/households/${hid}/members/${id}`),
      profile: this.api.get<any>(`/households/${hid}/members/${id}/profile`),
      otc: this.api.get<any[]>(`/households/${hid}/otc-medications`).pipe(empty),
      logs: this.api.get<any[]>(`/households/${hid}/logs?member_id=${id}`).pipe(empty),
      enrollments: this.api.get<any[]>(`/households/${hid}/enrollments?member_id=${id}`).pipe(empty),
      documents: this.api.get<any[]>(`/households/${hid}/documents?member_id=${id}`).pipe(empty),
      discipline: this.api.get<any[]>(`/households/${hid}/discipline?member_id=${id}`).pipe(empty),
    }).subscribe((bundle) => {
      this.member.set(bundle.member);
      this.profile.set(bundle.profile);
      this.otcCatalog.set(bundle.otc as any[]);
      this.otcId = '';
      this.logs.set(bundle.logs as any[]);
      this.enrollments.set(bundle.enrollments as any[]);
      this.documents.set(bundle.documents as any[]);
      this.discipline.set(bundle.discipline as any[]);
      this.editing.set(false);
      this.adding.set(null);
      this.editingMedId.set(null);
      this.loadPermissions(id);
    });
  }

  canManagePermissions(): boolean {
    const member = this.member();
    return (
      this.auth.isHouseholdAdmin() &&
      Boolean(member?.email || member?.login_status === 'linked' || member?.login_status === 'pending')
    );
  }

  hasGrant(resource: string, action: string): boolean {
    return this.permSet().has(`${resource}:${action}`);
  }

  toggleGrant(resource: string, action: string, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    const next = new Set(this.permSet());
    const key = `${resource}:${action}`;
    if (checked) {
      next.add(key);
    } else {
      next.delete(key);
    }
    this.permSet.set(next);
  }

  savePermissions(): void {
    const grants = [...this.permSet()].map((key) => {
      const [resource, action] = key.split(':');
      return { resource, action };
    });
    this.api
      .put(`/households/${this.api.hid()}/members/${this.memberId()}/permissions`, { grants })
      .subscribe();
  }

  private loadPermissions(id: string): void {
    if (!this.auth.isHouseholdAdmin()) {
      return;
    }
    forkJoin({
      catalog: this.api.get<PermResource[]>('/permission-catalog'),
      grants: this.api.get<{ resource: string; action: string }[]>(
        `/households/${this.api.hid()}/members/${id}/permissions`,
      ),
    }).subscribe((bundle) => {
      this.catalog.set(bundle.catalog);
      this.permSet.set(new Set(bundle.grants.map((item) => `${item.resource}:${item.action}`)));
    });
  }

  save(): void {
    const id = this.memberId();
    const hid = this.api.hid();
    this.api.patch(`/households/${hid}/members/${id}/profile`, this.draft).subscribe(() => {
      this.api
        .patch(`/households/${hid}/members/${id}`, {
          household_role: this.draft.household_role,
          email: this.draft.email || null,
        })
        .subscribe(() => this.reload(id));
    });
  }

  add(collection: string, payload: any): void {
    const id = this.memberId();
    const body =
      collection === 'medications'
        ? this.medPayload(payload)
        : payload;
    this.api.post(`/households/${this.api.hid()}/members/${id}/${collection}`, body).subscribe(() => {
      this.resetDraft(collection);
      this.reload(id);
    });
  }

  saveMedication(): void {
    const id = this.memberId();
    const editId = this.editingMedId();
    const body = this.medPayload(this.med);
    const request = editId
      ? this.api.patch(`/households/${this.api.hid()}/members/${id}/medications/${editId}`, body)
      : this.api.post(`/households/${this.api.hid()}/members/${id}/medications`, body);
    request.subscribe(() => {
      this.resetDraft('medications');
      this.reload(id);
    });
  }

  startEditMed(med: any): void {
    const parsed = parseDose(med.dose);
    this.med = {
      ...this.emptyMed(),
      ...med,
      dose_amount: parsed.amount ?? '',
      dose_unit: parsed.unit,
      flags: [...(med.flags ?? [])],
    };
    this.medTimes = (med.schedule_times ?? []).join(', ');
    this.editingMedId.set(med.id);
    this.adding.set('medications');
  }

  hasFlag(code: string): boolean {
    return (this.med.flags ?? []).includes(code);
  }

  toggleFlag(code: string, checked: boolean): void {
    const current = new Set(this.med.flags ?? []);
    if (checked) {
      current.add(code);
    } else {
      current.delete(code);
    }
    this.med.flags = [...current];
  }

  filteredMeds(profile: any): any[] {
    return (profile.medications ?? []).filter((med: any) => {
      const current = isAdministerable(med);
      if (this.medFilter() === 'active') {
        return current;
      }
      if (this.medFilter() === 'inactive') {
        return !current;
      }
      return true;
    });
  }

  flagName(code: string): string {
    return flagLabel(code);
  }

  remove(collection: string, itemId: string): void {
    const id = this.memberId();
    this.api.delete(`/households/${this.api.hid()}/members/${id}/${collection}/${itemId}`).subscribe(() => this.reload(id));
  }

  availableOtc(): any[] {
    const assigned = new Set(
      (this.profile()?.otc_medications ?? []).map((item: any) => item.otc_medication_id),
    );
    return this.otcCatalog().filter((item) => item.active !== false && !assigned.has(item.id));
  }

  assignOtc(): void {
    if (!this.otcId) {
      return;
    }
    const id = this.memberId();
    this.api
      .post(`/households/${this.api.hid()}/members/${id}/otc-medications`, {
        otc_medication_id: this.otcId,
      })
      .subscribe(() => this.reload(id));
  }

  removeOtc(assignmentId: string): void {
    const id = this.memberId();
    this.api
      .delete(`/households/${this.api.hid()}/members/${id}/otc-medications/${assignmentId}`)
      .subscribe(() => this.reload(id));
  }

  onPhoto(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }
    const id = this.memberId();
    const form = new FormData();
    form.append('file', file);
    this.api.upload(`/households/${this.api.hid()}/members/${id}/photo`, form).subscribe(() => {
      this.reload(id);
      input.value = '';
    });
  }

  private resetDraft(collection: string): void {
    if (collection === 'medications') {
      this.med = this.emptyMed();
      this.medTimes = '08:00';
      this.editingMedId.set(null);
      this.adding.set(null);
    }
    if (collection === 'allergies') this.allergy = this.emptyAllergy();
    if (collection === 'diagnoses') this.diagnosis = this.emptyDiagnosis();
    if (collection === 'disabilities') this.disability = this.emptyDisability();
    if (collection === 'clinicians') this.clinician = this.emptyClinician();
    if (collection === 'professional_contacts') this.pro = this.emptyPro();
    if (collection === 'emergency_contacts') this.emergency = this.emptyEmergency();
  }

  private medPayload(payload: any): any {
    const { dose_amount, dose_unit, ...rest } = payload;
    return {
      ...rest,
      dose: composeDose(dose_amount, dose_unit),
      schedule_times: this.medTimes.split(',').map((item) => item.trim()).filter(Boolean),
      start_date: payload.start_date || null,
      end_date: payload.end_date || null,
      hold_reason: payload.hold_reason || null,
      diagnosis: payload.diagnosis || null,
      instructions: payload.instructions || null,
      prescriber: payload.prescriber || null,
    };
  }

  private emptyMed() {
    return {
      name: '',
      dose_amount: '1',
      dose_unit: 'mg',
      route: 'oral',
      frequency: 'daily',
      instructions: '',
      is_psychotropic: false,
      is_prn: false,
      prescriber: '',
      diagnosis: '',
      start_date: '',
      end_date: '',
      hold_reason: '',
      active: true,
      flags: [] as string[],
    };
  }
  private emptyAllergy() {
    return { allergen: '', severity: 'moderate', reaction: '' };
  }
  private emptyDiagnosis() {
    return { name: '', code: '' };
  }
  private emptyDisability() {
    return { name: '', accommodations: '' };
  }
  private emptyClinician() {
    return { role: 'pcp', name: '', phone: '', clinic: '' };
  }
  private emptyPro() {
    return { role: 'case_worker', name: '', agency: '', phone: '' };
  }
  private emptyEmergency() {
    return { name: '', relationship: '', phone: '', is_primary: false };
  }
}
