from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.exports.ar_dcfs_forms import (
    foster_home_log_pdf,
    journal_entries_pdf,
    personal_belonging_pdf,
    weekly_med_chart_pdf,
)
from app.exports.catalog import get_official_export, list_official_exports
from app.exports.pdfs import (
    initials_cell,
    medication_log_pdf,
    quarterly_drills_pdf,
    sibling_contact_pdf,
)
from app.models import (
    Household,
    HouseholdMember,
    HouseholdOtcMedication,
    LogEntry,
    Medication,
)
from app.services.households import HouseholdService, legal_name
from app.services.operations import LogService
from app.services.timezones import format_clock_12h, local_date, local_time_hm


def _initials(name: str) -> str:
    parts = [part for part in name.split() if part]
    return "".join(part[0].upper() for part in parts[:2])


def _member_name(db: Session, member_id: str | None) -> str:
    if not member_id:
        return ""
    member = db.get(HouseholdMember, member_id)
    return legal_name(member.profile) if member else member_id


def _resolve_label(db: Session, value: str) -> str:
    member = db.get(HouseholdMember, value)
    if member is not None:
        return legal_name(member.profile)
    return value


def _join_names(names: list[str]) -> str:
    if len(names) <= 2:
        return " and ".join(names)
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def _clock_cfs400(value: str) -> str:
    return format_clock_12h(value).replace(" AM", " a.m.").replace(" PM", " p.m.")


def _contact_when(day: str, start: str, end: str) -> str:
    try:
        stamp = date.fromisoformat(day).strftime("%m-%d-%y")
    except ValueError:
        stamp = day
    start_s = _clock_cfs400(start)
    end_s = _clock_cfs400(end)
    if start_s and end_s:
        return f"{stamp} @ {start_s}-{end_s}"
    if start_s:
        return f"{stamp} @ {start_s}".strip()
    return stamp


class OfficialExportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.logs = LogService(db)
        self.households = HouseholdService(db)

    def list_forms(self) -> list[dict]:
        return [
            {
                "code": item.code,
                "name": item.name,
                "description": item.description,
                "category": item.category,
                "source_forms": list(item.source_forms),
            }
            for item in list_official_exports()
        ]

    def export_pdf(
        self,
        household_id: str,
        form_code: str,
        start_date: date,
        end_date: date,
        member_ids: list[str],
    ) -> bytes:
        spec = get_official_export(form_code)
        selected = list(member_ids)
        if not selected:
            selected = [
                member.id
                for member in self.households.list_members(household_id)
                if member.status == "active"
            ]
        entries = self.logs.list_logs(
            household_id,
            form_type_codes=spec.source_forms,
            status="submitted",
            occurred_from=start_date,
            occurred_to=end_date,
        )
        tz_name = self._timezone(household_id)
        if spec.code == "ar_dcfs_quarterly_drills":
            return quarterly_drills_pdf(self._drill_rows(entries, tz_name))
        if spec.code == "ar_dcfs_sibling_contact":
            return sibling_contact_pdf(
                self._sibling_home_line(household_id),
                self._sibling_rows(entries, selected),
            )
        if spec.code == "ar_dcfs_weekly_med_chart":
            return weekly_med_chart_pdf(
                self._weekly_med_pages(entries, selected, tz_name)
            )
        if spec.code == "ar_dcfs_journal_entries":
            return journal_entries_pdf(self._journal_pages(entries, selected))
        if spec.code == "ar_dcfs_personal_belonging":
            child_id = selected[0] if selected else ""
            return personal_belonging_pdf(
                _member_name(self.db, child_id),
                self._belonging_items(entries, child_id),
            )
        if spec.code == "ar_dcfs_foster_home_log":
            return self._foster_home_log(entries, start_date, tz_name)
        return medication_log_pdf(self._medication_pages(entries, selected, tz_name))

    def _timezone(self, household_id: str) -> str:
        household = self.db.get(Household, household_id)
        return (
            household.timezone
            if household and household.timezone
            else "America/Chicago"
        )

    def _drill_rows(
        self, entries: list[LogEntry], tz_name: str
    ) -> list[tuple[str, str, str]]:
        rows: list[tuple[str, str, str]] = []
        for entry in sorted(entries, key=lambda item: item.occurred_at):
            names = [
                _resolve_label(self.db, str(value))
                for value in entry.payload.get("participants") or []
            ]
            when = (
                entry.payload.get("date")
                or local_date(entry.occurred_at, tz_name).isoformat()
            )
            start = entry.payload.get("start_time") or ""
            stamp = f"{when} {start}".strip()
            seconds = entry.payload.get("evacuation_seconds")
            duration = f"{seconds} seconds" if seconds not in (None, "") else ""
            rows.append((stamp, ", ".join(names), duration))
        return rows

    def _sibling_home_line(self, household_id: str) -> str:
        household = self.db.get(Household, household_id)
        if household is None:
            return ""
        name = household.name or ""
        provider = household.license_number or ""
        if name and provider:
            return f"{name} / {provider}"
        return name or provider

    def _sibling_rows(
        self, entries: list[LogEntry], selected: list[str]
    ) -> list[tuple[str, str, str, str]]:
        wanted = {item for item in selected if item}
        rows: list[tuple[str, str, str, str]] = []
        for entry in sorted(entries, key=lambda item: item.occurred_at):
            in_home_ids = [
                str(value) for value in entry.payload.get("siblings_in_home") or []
            ]
            if wanted and not wanted.intersection(in_home_ids):
                continue
            in_home = [_resolve_label(self.db, value) for value in in_home_ids]
            others = [
                str(value).strip()
                for value in entry.payload.get("other_siblings") or []
            ]
            names = [item for item in [*in_home, *others] if item]
            rows.append(
                (
                    _contact_when(
                        str(entry.payload.get("date") or ""),
                        str(entry.payload.get("start_time") or ""),
                        str(entry.payload.get("end_time") or ""),
                    ),
                    _join_names(names),
                    str(entry.payload.get("contact_type") or ""),
                    str(entry.payload.get("notes") or ""),
                )
            )
        return rows

    def _medication_pages(
        self, entries: list[LogEntry], selected: list[str], tz_name: str
    ) -> list[tuple[str, list[tuple[str, str, str, str, str, str]]]]:
        pages: list[tuple[str, list[tuple]]] = []
        for member_id in selected:
            child = _member_name(self.db, member_id)
            rows: list[tuple] = []
            for entry in sorted(entries, key=lambda item: item.occurred_at):
                if entry.subject_member_id != member_id:
                    continue
                if entry.payload.get("outcome") not in (None, "", "given"):
                    continue
                caregiver = _member_name(self.db, entry.recorded_by_id)
                drawn_fp = str(entry.payload.get("fp_initials") or "").strip()
                drawn_fc = str(entry.payload.get("fc_initials") or "").strip()
                rows.append(
                    (
                        str(entry.payload.get("medication_name") or ""),
                        str(entry.payload.get("dose_given") or ""),
                        local_date(entry.occurred_at, tz_name).isoformat(),
                        local_time_hm(entry.occurred_at, tz_name),
                        initials_cell(drawn_fp) if drawn_fp else _initials(caregiver),
                        initials_cell(drawn_fc) if drawn_fc else "",
                    )
                )
            pages.append((child, rows))
        return pages

    def _weekly_med_pages(
        self, entries: list[LogEntry], selected: list[str], tz_name: str
    ) -> list[tuple[str, str, str, list[dict]]]:
        pages: list[tuple[str, str, str, list[dict]]] = []
        for member_id in selected:
            weeks: dict[date, dict[str, dict]] = {}
            for entry in sorted(entries, key=lambda item: item.occurred_at):
                if entry.subject_member_id != member_id:
                    continue
                if entry.payload.get("outcome") not in (None, "", "given"):
                    continue
                day = local_date(entry.occurred_at, tz_name)
                week = _week_start_sunday(day)
                med_id = str(entry.payload.get("medication_id") or "")
                name = str(entry.payload.get("medication_name") or "")
                key = med_id or name
                bucket = weeks.setdefault(week, {})
                med = bucket.setdefault(
                    key,
                    {
                        "name": name,
                        "dose": str(entry.payload.get("dose_given") or ""),
                        "frequency": self._medication_frequency(med_id),
                        "days": {},
                    },
                )
                initial = _dose_initial(entry, self.db)
                day_index = (day.weekday() + 1) % 7
                med["days"].setdefault(day_index, []).append(
                    (local_time_hm(entry.occurred_at, tz_name), initial)
                )
            for week in sorted(weeks):
                meds = list(weeks[week].values())
                overflow: list[dict] = []
                normalized: list[dict] = []
                for med in meds:
                    extra = _split_extra_dose_rows(med)
                    normalized.append(med)
                    overflow.extend(extra)
                all_meds = [*normalized, *overflow]
                end = week + timedelta(days=6)
                stamp = _slash_date(week)
                end_stamp = _slash_date(end)
                child = _member_name(self.db, member_id)
                if not all_meds:
                    pages.append((child, stamp, end_stamp, []))
                    continue
                for index in range(0, len(all_meds), 4):
                    pages.append((child, stamp, end_stamp, all_meds[index : index + 4]))
        return pages

    def _medication_frequency(self, medication_id: str) -> str:
        if not medication_id:
            return ""
        med = self.db.get(Medication, medication_id)
        if med is not None:
            return med.frequency
        otc = self.db.get(HouseholdOtcMedication, medication_id)
        if otc is not None:
            return "as needed"
        return ""

    def _journal_pages(
        self, entries: list[LogEntry], selected: list[str]
    ) -> list[tuple[str, list[tuple[str, str, str]]]]:
        wanted = {item for item in selected if item}
        pages: list[tuple[str, list[tuple[str, str, str]]]] = []
        for member_id in selected:
            rows: list[tuple[str, str, str]] = []
            for entry in sorted(entries, key=lambda item: item.occurred_at):
                if wanted and entry.subject_member_id not in wanted:
                    continue
                if entry.subject_member_id != member_id:
                    continue
                day = str(entry.payload.get("date") or "")
                clock = format_clock_12h(str(entry.payload.get("time") or ""))
                rows.append((day, clock, str(entry.payload.get("incident") or "")))
            pages.append((_member_name(self.db, member_id), rows))
        return pages

    def _belonging_items(
        self, entries: list[LogEntry], child_id: str
    ) -> list[tuple[str, str, str, str, str]]:
        items: list[tuple[str, str, str, str, str]] = []
        for entry in sorted(entries, key=lambda item: item.occurred_at):
            if child_id and entry.subject_member_id != child_id:
                continue
            recorded = str(entry.payload.get("recorded_on") or "")
            initials = str(entry.payload.get("initials") or "")
            stamp = " ".join(part for part in (recorded, initials) if part)
            items.append(
                (
                    str(entry.payload.get("item_category") or ""),
                    str(entry.payload.get("description") or ""),
                    str(entry.payload.get("quantity") or ""),
                    stamp,
                    str(entry.payload.get("disposition") or ""),
                )
            )
        return items

    def _foster_home_log(
        self, entries: list[LogEntry], start_date: date, tz_name: str
    ) -> bytes:
        month_name = start_date.strftime("%B")
        trainings: list[str] = []
        drills: list[str] = []
        visits: list[tuple[str, str, str]] = []
        for entry in sorted(entries, key=lambda item: item.occurred_at):
            if entry.form_type_code == "training":
                day = str(entry.payload.get("date") or "")
                topic = str(entry.payload.get("topic") or "")
                hours = str(entry.payload.get("hours") or "")
                notes = str(entry.payload.get("notes") or "")
                extra = f" ({hours} hrs)" if hours else ""
                note = f" — {notes}" if notes else ""
                trainings.append(f"{day}  {topic}{extra}{note}".strip())
            elif entry.form_type_code == "fire_drill":
                names = [
                    _resolve_label(self.db, str(value))
                    for value in entry.payload.get("participants") or []
                ]
                when = str(entry.payload.get("date") or "")
                start = format_clock_12h(str(entry.payload.get("start_time") or ""))
                seconds = entry.payload.get("evacuation_seconds")
                duration = f"{seconds} seconds" if seconds not in (None, "") else ""
                drills.append(
                    " · ".join(
                        part
                        for part in (when, start, ", ".join(names), duration)
                        if part
                    )
                )
            elif entry.form_type_code == "case_worker_visit":
                when = local_date(entry.occurred_at, tz_name).isoformat()
                worker = str(entry.payload.get("worker_name") or "")
                children = [
                    _resolve_label(self.db, str(value))
                    for value in entry.payload.get("children_visited") or []
                ]
                if children:
                    for child in children:
                        visits.append((child, when, worker))
                else:
                    visits.append(("", when, worker))
        return foster_home_log_pdf(month_name, trainings, drills, visits)


def _week_start_sunday(day: date) -> date:
    return day - timedelta(days=(day.weekday() + 1) % 7)


def _slash_date(day: date) -> str:
    return day.strftime("%m/%d/%y")


def _dose_initial(entry: LogEntry, db: Session) -> str:
    drawn = str(entry.payload.get("fp_initials") or "").strip()
    if drawn:
        return drawn
    return _initials(_member_name(db, entry.recorded_by_id))


def _split_extra_dose_rows(med: dict) -> list[dict]:
    extras: list[dict] = []
    overflow_days: dict[int, list[tuple[str, str]]] = {}
    for day_index, entries in list(med.get("days", {}).items()):
        if len(entries) > 2:
            overflow_days[day_index] = entries[2:]
            med["days"][day_index] = entries[:2]
    if not overflow_days:
        return extras
    extras.append(
        {
            "name": med.get("name"),
            "dose": med.get("dose"),
            "frequency": med.get("frequency"),
            "days": overflow_days,
        }
    )
    extras.extend(_split_extra_dose_rows(extras[-1]))
    return extras
