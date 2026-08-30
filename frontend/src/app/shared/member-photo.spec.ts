import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { MemberPhoto } from './member-photo';

describe('MemberPhoto', () => {
  let fixture: ComponentFixture<MemberPhoto>;
  let http: HttpTestingController;

  beforeEach(async () => {
    URL.createObjectURL = () => 'blob:fake-photo';
    URL.revokeObjectURL = () => undefined;
    await TestBed.configureTestingModule({
      imports: [MemberPhoto],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(MemberPhoto);
    fixture.componentRef.setInput('householdId', 'h1');
    fixture.componentRef.setInput('memberId', 'm1');
    fixture.componentRef.setInput('name', 'Casey Child');
  });

  afterEach(() => {
    http.verify();
  });

  it('shows initials when the member has no photo', async () => {
    fixture.componentRef.setInput('hasPhoto', false);
    fixture.detectChanges();
    await fixture.whenStable();
    expect(fixture.nativeElement.textContent).toContain('CC');
    expect(fixture.nativeElement.querySelector('img')).toBeNull();
  });

  it('loads the profile photo when hasPhoto is true', async () => {
    fixture.componentRef.setInput('hasPhoto', true);
    fixture.detectChanges();
    const request = http.expectOne('/api/households/h1/members/m1/photo');
    request.flush(new Blob(['fake-image'], { type: 'image/png' }));
    fixture.detectChanges();
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelector('img')).toBeTruthy();
  });
});
