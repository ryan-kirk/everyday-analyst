from __future__ import annotations

from typing import TypedDict

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.preset import Preset


class PresetTemplate(TypedDict):
    name: str
    series_a: str
    series_b: str
    recommended_date_range: str
    description: str


DEFAULT_PRESETS: list[PresetTemplate] = [
    {
        "name": "Fed Watch",
        "series_a": "DGS2",
        "series_b": "T10Y2Y",
        "recommended_date_range": "1y",
        "description": (
            "Track short-term Treasury yields with the 10Y-2Y spread to monitor rate expectations "
            "and curve steepening/flattening conditions."
        ),
    },
    {
        "name": "Inflation vs Rates",
        "series_a": "CPIAUCSL",
        "series_b": "DGS2",
        "recommended_date_range": "3y",
        "description": (
            "Compare inflation trend against 2-year Treasury yields to see whether rates are "
            "moving in line with inflation pressure."
        ),
    },
    {
        "name": "Housing vs Mortgage Rates",
        "series_a": "HOUST",
        "series_b": "MORTGAGE30US",
        "recommended_date_range": "5y",
        "description": (
            "View housing starts against 30-year mortgage rates to inspect affordability "
            "and potential housing activity slowdowns."
        ),
    },
    {
        "name": "Labor Market vs Rates",
        "series_a": "UNRATE",
        "series_b": "DGS2",
        "recommended_date_range": "3y",
        "description": (
            "Compare unemployment dynamics with short-term rates to explore labor-market context "
            "during tightening and easing cycles."
        ),
    },
    {
        "name": "Growth vs Rates",
        "series_a": "INDPRO",
        "series_b": "DGS10",
        "recommended_date_range": "5y",
        "description": (
            "Compare industrial production growth with 10-year yields to understand longer-cycle "
            "growth and rate environments."
        ),
    },
    {
        "name": "Market Stress",
        "series_a": "SP500",
        "series_b": "VIXCLS",
        "recommended_date_range": "1y",
        "description": (
            "Compare equity prices with implied volatility to inspect risk-on/risk-off regimes "
            "during market stress windows."
        ),
    },
    {
        "name": "Sentiment vs Spending",
        "series_a": "UMCSENT",
        "series_b": "RSAFS",
        "recommended_date_range": "5y",
        "description": (
            "Track consumer sentiment alongside retail spending to compare confidence "
            "and demand trends."
        ),
    },
    {
        "name": "Housing Permits vs Applications",
        "series_a": "PERMIT",
        "series_b": "M0264AUSM500NNBR",
        "recommended_date_range": "5y",
        "description": (
            "Compare housing permits and mortgage applications as an early read on "
            "housing demand momentum."
        ),
    },
    {
        "name": "Local Migration vs Permits",
        "series_a": "NETMIGNACS006037",
        "series_b": "BPPRIV006037",
        "recommended_date_range": "5y",
        "description": (
            "Compare county migration flow and local housing permits for regional "
            "population and supply context."
        ),
    },
]


def ensure_default_presets(db: Session) -> None:
    existing = {row.name: row for row in db.scalars(select(Preset)).all()}

    changed = False
    for template in DEFAULT_PRESETS:
        current = existing.get(template["name"])
        if current is None:
            db.add(
                Preset(
                    name=template["name"],
                    series_a=template["series_a"],
                    series_b=template["series_b"],
                    recommended_date_range=template["recommended_date_range"],
                    description=template["description"],
                    is_active=True,
                )
            )
            changed = True
            continue

        if (
            current.series_a != template["series_a"]
            or current.series_b != template["series_b"]
            or current.recommended_date_range != template["recommended_date_range"]
            or current.description != template["description"]
            or current.is_active is not True
        ):
            current.series_a = template["series_a"]
            current.series_b = template["series_b"]
            current.recommended_date_range = template["recommended_date_range"]
            current.description = template["description"]
            current.is_active = True
            changed = True

    if changed:
        db.commit()


def list_presets(db: Session) -> list[Preset]:
    stmt: Select[tuple[Preset]] = (
        select(Preset).where(Preset.is_active.is_(True)).order_by(Preset.name.asc())
    )
    return list(db.scalars(stmt).all())
