from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from datetime import date, timedelta
from math import sqrt

from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.series import Series
from app.schemas.event import EventRead
from app.schemas.insights import (
    InsightInflectionPoint,
    InsightMajorMovement,
    InsightsResponse,
)
from app.services.compare_service import get_aligned_observations, get_events_in_range


@dataclass(frozen=True)
class _SeriesPoint:
    date: date
    value: float


def generate_insights(
    db: Session,
    series_a: Series,
    series_b: Series,
    start: date | None = None,
    end: date | None = None,
) -> InsightsResponse:
    aligned = get_aligned_observations(
        db=db,
        series_a_id=series_a.id,
        series_b_id=series_b.id,
        start=start,
        end=end,
    )

    effective_start = start or (aligned[0].date if aligned else None)
    effective_end = end or (aligned[-1].date if aligned else None)
    events = (
        get_events_in_range(db=db, start=effective_start, end=effective_end)
        if (effective_start is not None or effective_end is not None)
        else []
    )

    points_a = [_SeriesPoint(date=row.date, value=row.value_a) for row in aligned if row.value_a is not None]
    points_b = [_SeriesPoint(date=row.date, value=row.value_b) for row in aligned if row.value_b is not None]
    overlap_pairs, overlap_method = _build_overlap_pairs(points_a, points_b)

    correlation = _calculate_pearson(overlap_pairs)
    inflections = _detect_inflections(points_a, series_a.name, events) + _detect_inflections(
        points_b, series_b.name, events
    )
    inflections.sort(key=lambda row: row.date)

    major_moves = _detect_major_movements(points_a, series_a.name, events) + _detect_major_movements(
        points_b, series_b.name, events
    )
    major_moves.sort(key=lambda row: row.end_date)

    summary = _build_narrative_summary(
        series_a=series_a,
        series_b=series_b,
        start=effective_start,
        end=effective_end,
        aligned_points=len(aligned),
        overlap_points=len(overlap_pairs),
        overlap_method=overlap_method,
        correlation=correlation,
        inflections=inflections,
        major_moves=major_moves,
    )

    return InsightsResponse(
        series_a=series_a,
        series_b=series_b,
        start=effective_start,
        end=effective_end,
        aligned_points=len(aligned),
        series_a_points=len(points_a),
        series_b_points=len(points_b),
        overlap_points=len(overlap_pairs),
        overlap_method=overlap_method,
        correlation=correlation,
        inflection_points=inflections,
        major_movements=major_moves,
        narrative_summary=summary,
    )


def _calculate_pearson(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 2:
        return None

    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)

    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator_x = sum((x - mean_x) ** 2 for x in xs)
    denominator_y = sum((y - mean_y) ** 2 for y in ys)
    denominator = sqrt(denominator_x * denominator_y)

    if denominator == 0:
        return None
    return numerator / denominator


def _build_overlap_pairs(
    points_a: list[_SeriesPoint],
    points_b: list[_SeriesPoint],
) -> tuple[list[tuple[float, float]], str]:
    if not points_a or not points_b:
        return [], "none"

    values_b_by_date = {point.date: point.value for point in points_b}
    exact_pairs = [
        (point.value, values_b_by_date[point.date]) for point in points_a if point.date in values_b_by_date
    ]

    min_reasonable_exact = max(12, min(len(points_a), len(points_b)) // 4)
    if len(exact_pairs) >= min_reasonable_exact:
        return exact_pairs, "exact_date"

    nearest_pairs = _build_nearest_date_pairs(points_a, points_b, max_gap_days=21)
    if len(nearest_pairs) > len(exact_pairs):
        return nearest_pairs, "nearest_date_21d"
    return exact_pairs, "exact_date"


def _build_nearest_date_pairs(
    points_a: list[_SeriesPoint],
    points_b: list[_SeriesPoint],
    *,
    max_gap_days: int,
) -> list[tuple[float, float]]:
    if not points_a or not points_b:
        return []

    primary_is_a = len(points_a) <= len(points_b)
    primary = points_a if primary_is_a else points_b
    secondary = points_b if primary_is_a else points_a
    secondary_dates = [point.date for point in secondary]

    used_secondary_indices: set[int] = set()
    pairs: list[tuple[float, float]] = []

    for primary_point in primary:
        center = bisect_left(secondary_dates, primary_point.date)
        window_start = max(0, center - 2)
        window_end = min(len(secondary), center + 3)
        candidates = list(range(window_start, window_end))
        candidates.sort(key=lambda idx: abs((secondary[idx].date - primary_point.date).days))

        chosen_index: int | None = None
        for idx in candidates:
            if idx in used_secondary_indices:
                continue
            if abs((secondary[idx].date - primary_point.date).days) > max_gap_days:
                continue
            chosen_index = idx
            break

        if chosen_index is None:
            continue

        used_secondary_indices.add(chosen_index)
        secondary_point = secondary[chosen_index]
        if primary_is_a:
            pairs.append((primary_point.value, secondary_point.value))
        else:
            pairs.append((secondary_point.value, primary_point.value))

    return pairs


def _detect_inflections(
    points: list[_SeriesPoint],
    series_name: str,
    events: list[Event],
    max_points: int = 6,
) -> list[InsightInflectionPoint]:
    if len(points) < 3:
        return []

    ranked: list[tuple[float, InsightInflectionPoint]] = []
    for index in range(2, len(points)):
        prev_delta = points[index - 1].value - points[index - 2].value
        curr_delta = points[index].value - points[index - 1].value

        if prev_delta == 0 or curr_delta == 0:
            continue
        if prev_delta > 0 and curr_delta < 0:
            direction = "downturn"
        elif prev_delta < 0 and curr_delta > 0:
            direction = "upturn"
        else:
            continue

        inflection = InsightInflectionPoint(
            date=points[index].date,
            series=series_name,
            direction=direction,
            delta=curr_delta,
            nearby_events=_nearby_events(events, points[index].date),
        )
        ranked.append((abs(curr_delta - prev_delta), inflection))

    ranked.sort(key=lambda item: item[0], reverse=True)
    top = [item[1] for item in ranked[:max_points]]
    top.sort(key=lambda item: item.date)
    return top


def _detect_major_movements(
    points: list[_SeriesPoint],
    series_name: str,
    events: list[Event],
    max_moves: int = 4,
) -> list[InsightMajorMovement]:
    if len(points) < 2:
        return []

    ranked: list[tuple[float, InsightMajorMovement]] = []
    for index in range(1, len(points)):
        prev_point = points[index - 1]
        curr_point = points[index]
        change = curr_point.value - prev_point.value

        percent_change: float | None = None
        if prev_point.value != 0:
            percent_change = change / abs(prev_point.value)
        magnitude = abs(percent_change) if percent_change is not None else abs(change)

        # Ignore tiny day-to-day noise so the output stays interpretable.
        if percent_change is not None and abs(percent_change) < 0.015 and abs(change) < 0.05:
            continue

        movement = InsightMajorMovement(
            series=series_name,
            start_date=prev_point.date,
            end_date=curr_point.date,
            change=change,
            percent_change=percent_change,
            direction="increase" if change >= 0 else "decrease",
            nearby_events=_nearby_events(events, curr_point.date),
        )
        ranked.append((magnitude, movement))

    ranked.sort(key=lambda item: item[0], reverse=True)
    top = [item[1] for item in ranked[:max_moves]]
    top.sort(key=lambda item: item.end_date)
    return top


def _nearby_events(
    events: list[Event],
    focus_date: date,
    window_days: int = 3,
    max_events: int = 3,
) -> list[EventRead]:
    start = focus_date - timedelta(days=window_days)
    end = focus_date + timedelta(days=window_days)
    nearby = [event for event in events if start <= event.event_date <= end]
    nearby.sort(key=lambda event: abs((event.event_date - focus_date).days))
    return [EventRead.model_validate(event) for event in nearby[:max_events]]


def _build_narrative_summary(
    *,
    series_a: Series,
    series_b: Series,
    start: date | None,
    end: date | None,
    aligned_points: int,
    overlap_points: int,
    overlap_method: str,
    correlation: float | None,
    inflections: list[InsightInflectionPoint],
    major_moves: list[InsightMajorMovement],
) -> str:
    range_text = "the selected range"
    if start and end:
        range_text = f"{start.isoformat()} to {end.isoformat()}"
    elif start:
        range_text = f"{start.isoformat()} onward"
    elif end:
        range_text = f"up to {end.isoformat()}"

    if overlap_method == "nearest_date_21d":
        overlap_note = " using nearest-date matching (up to 21 days) to adjust for different reporting frequencies."
    elif overlap_method == "exact_date":
        overlap_note = " using exact same-day observations."
    else:
        overlap_note = "."

    parts = [
        (
            f"Across {range_text}, {series_a.name} and {series_b.name} produced "
            f"{aligned_points} aligned dates with {overlap_points} overlapping values{overlap_note}"
        )
    ]

    if correlation is None:
        parts.append("Correlation could not be estimated because overlap is too sparse.")
    else:
        relation = "positive" if correlation > 0 else "negative" if correlation < 0 else "flat"
        strength = "strong" if abs(correlation) >= 0.7 else "moderate" if abs(correlation) >= 0.4 else "weak"
        parts.append(f"Observed correlation is {correlation:.2f}, indicating a {strength} {relation} relationship.")

    if major_moves:
        strongest = max(
            major_moves,
            key=lambda move: abs(move.percent_change) if move.percent_change is not None else abs(move.change),
        )
        if strongest.percent_change is not None:
            move_text = f"{strongest.percent_change * 100:.1f}%"
        else:
            move_text = f"{strongest.change:.3f} units"
        parts.append(
            f"The largest one-step move was in {strongest.series} "
            f"from {strongest.start_date.isoformat()} to {strongest.end_date.isoformat()} "
            f"({move_text}, {strongest.direction})."
        )
        if strongest.nearby_events:
            event_titles = ", ".join(event.title for event in strongest.nearby_events[:2])
            parts.append(f"Nearby events around that move include {event_titles}.")
    elif inflections:
        first = inflections[0]
        parts.append(
            f"Detected {len(inflections)} inflection points; the earliest notable shift is "
            f"a {first.direction} in {first.series} on {first.date.isoformat()}."
        )
    else:
        parts.append("No major movements or inflection points were detected with the current thresholds.")

    return " ".join(parts)
