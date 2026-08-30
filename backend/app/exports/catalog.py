from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import DomainError


@dataclass(frozen=True)
class OfficialExport:
    code: str
    name: str
    description: str
    source_forms: tuple[str, ...]

    @property
    def category(self) -> str:
        if self.code.startswith("ar_dcfs"):
            return "Arkansas DCFS"
        return "Other"


OFFICIAL_EXPORTS: tuple[OfficialExport, ...] = (
    OfficialExport(
        code="ar_dcfs_quarterly_drills",
        name="Quarterly Fire/Tornado Drills",
        description="Arkansas DCFS quarterly fire and tornado drill log.",
        source_forms=("fire_drill", "tornado_drill"),
    ),
    OfficialExport(
        code="ar_dcfs_medication_log",
        name="Medication Dosage Logs",
        description="Arkansas DCFS medication dosage log by child.",
        source_forms=("medication_administration",),
    ),
    OfficialExport(
        code="ar_dcfs_sibling_contact",
        name="Separated Sibling Contact Report",
        description="Arkansas DCFS CFS-400 sibling contact log for foster parents.",
        source_forms=("sibling_contact",),
    ),
)

_BY_CODE = {item.code: item for item in OFFICIAL_EXPORTS}


def list_official_exports() -> list[OfficialExport]:
    return list(OFFICIAL_EXPORTS)


def get_official_export(code: str) -> OfficialExport:
    try:
        return _BY_CODE[code]
    except KeyError as exc:
        raise DomainError(f"Unknown export form: {code}") from exc
