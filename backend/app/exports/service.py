from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.exports.catalog import get_official_export, list_official_exports
from app.exports.pdfs import (
    initials_cell,
    medication_log_pdf,
    quarterly_drills_pdf,
    sibling_contact_pdf,
)
from app.models import Household, HouseholdMember, LogEntry
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
