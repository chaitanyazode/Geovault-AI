"""
GeoVault AI - Deterministic Analytics Engine ("Python Calculates")
Performs deterministic mathematical calculations: totals, averages, comparisons,
year-over-year deltas, target achievements, and multi-year trends.
"""

from typing import List, Dict, Any, Optional
from app.schemas.query import TrendPoint, TrendSummary, MineComparisonItem, AnalyticsResult


class AnalyticsEngine:
    """
    Dedicated calculation engine.
    Ensures mathematical accuracy and deterministic outputs across all analytical queries.
    """

    @staticmethod
    def _get_val(record: Any, key: str) -> Optional[float]:
        """Helper to extract float value from dict or SQLAlchemy model."""
        if isinstance(record, dict):
            val = record.get(key)
        else:
            val = getattr(record, key, None)
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    @classmethod
    def compute_total(cls, records: List[Any], metric_key: str) -> float:
        """Computes the exact sum of a metric across records."""
        total = 0.0
        for r in records:
            v = cls._get_val(r, metric_key)
            if v is not None:
                total += v
        return round(total, 3)

    @classmethod
    def compute_average(cls, records: List[Any], metric_key: str) -> Optional[float]:
        """Computes arithmetic mean of a metric."""
        vals = [cls._get_val(r, metric_key) for r in records if cls._get_val(r, metric_key) is not None]
        if not vals:
            return None
        return round(sum(vals) / len(vals), 3)

    @classmethod
    def compute_min_max(cls, records: List[Any], metric_key: str) -> Dict[str, Optional[float]]:
        """Finds minimum and maximum values."""
        vals = [cls._get_val(r, metric_key) for r in records if cls._get_val(r, metric_key) is not None]
        if not vals:
            return {"min": None, "max": None}
        return {"min": min(vals), "max": max(vals)}

    @classmethod
    def compute_target_achievement(cls, target: float, actual: float) -> Dict[str, Any]:
        """
        Calculates target achievement percentage, variance, and shortfall/surplus.
        Variance = actual - target.
        """
        target = float(target) if target is not None else 0.0
        actual = float(actual) if actual is not None else 0.0

        if target <= 0:
            return {
                "target": target,
                "actual": actual,
                "variance": round(actual - target, 3),
                "achievement_pct": None,
                "status": "TARGET_NON_POSITIVE",
            }

        variance = round(actual - target, 3)
        achievement = round((actual / target) * 100.0, 2)
        return {
            "target": round(target, 3),
            "actual": round(actual, 3),
            "variance": variance,
            "achievement_pct": achievement,
            "shortfall_mt": round(max(0.0, target - actual), 3),
            "surplus_mt": round(max(0.0, actual - target), 3),
            "status": "ACHIEVED" if actual >= target else "SHORTFALL",
        }

    @classmethod
    def compute_yoy_series(
        cls,
        records: List[Any],
        time_key: str = "year",
        metric_key: str = "actual_production_mt",
        target_key: Optional[str] = "target_mt",
    ) -> List[TrendPoint]:
        """
        Sorts records chronologically and calculates year-over-year delta and growth rate.
        """
        # Sort records by time key
        sorted_recs = sorted(records, key=lambda x: cls._get_val(x, time_key) or 0)
        points: List[TrendPoint] = []

        prev_val: Optional[float] = None
        for r in sorted_recs:
            t_val = cls._get_val(r, time_key)
            m_val = cls._get_val(r, metric_key)
            if t_val is None or m_val is None:
                continue

            target_val = cls._get_val(r, target_key) if target_key else None

            delta = None
            growth_pct = None
            if prev_val is not None and prev_val != 0:
                delta = round(m_val - prev_val, 3)
                growth_pct = round((delta / prev_val) * 100.0, 2)

            points.append(
                TrendPoint(
                    time_label=int(t_val) if float(t_val).is_integer() else t_val,
                    value=round(m_val, 3),
                    target=round(target_val, 3) if target_val is not None else None,
                    yoy_change_mt=delta,
                    yoy_growth_pct=growth_pct,
                )
            )
            prev_val = m_val

        return points

    @classmethod
    def compute_trend_summary(
        cls,
        records: List[Any],
        time_key: str = "year",
        metric_key: str = "actual_production_mt",
        target_key: Optional[str] = "target_mt",
    ) -> Optional[TrendSummary]:
        """
        Computes overall multi-period trend direction, net change, and extremes.
        """
        series = cls.compute_yoy_series(records, time_key=time_key, metric_key=metric_key, target_key=target_key)
        if len(series) < 2:
            return None

        start_pt = series[0]
        end_pt = series[-1]
        net_change = round(end_pt.value - start_pt.value, 3)
        net_change_pct = round((net_change / start_pt.value) * 100.0, 2) if start_pt.value != 0 else 0.0

        min_pt = min(series, key=lambda p: p.value)
        max_pt = max(series, key=lambda p: p.value)

        # Determine trajectory direction
        all_increasing = all(p.yoy_change_mt is None or p.yoy_change_mt >= 0 for p in series[1:])
        all_decreasing = all(p.yoy_change_mt is None or p.yoy_change_mt <= 0 for p in series[1:])

        if abs(net_change_pct) < 1.0:
            direction = "FLAT"
        elif all_increasing:
            direction = "UPWARD"
        elif all_decreasing:
            direction = "DOWNWARD"
        else:
            direction = "FLUCTUATING"

        return TrendSummary(
            direction=direction,
            start_value=start_pt.value,
            end_value=end_pt.value,
            net_change=net_change,
            net_change_pct=net_change_pct,
            min_point={"time": start_pt.time_label if min_pt == start_pt else min_pt.time_label, "value": min_pt.value},
            max_point={"time": max_pt.time_label, "value": max_pt.value},
            series=series,
        )

    @classmethod
    def compare_mines(
        cls,
        records: List[Any],
        mine_names_map: Optional[Dict[str, str]] = None,
    ) -> List[MineComparisonItem]:
        """
        Aggregates production, targets, and availability per mine for comparison.
        """
        by_mine: Dict[str, List[Any]] = {}
        for r in records:
            m_code = r.get("mine_code") if isinstance(r, dict) else getattr(r, "mine_code", None)
            if not m_code:
                continue
            if m_code not in by_mine:
                by_mine[m_code] = []
            by_mine[m_code].append(r)

        items: List[MineComparisonItem] = []
        for m_code, m_records in by_mine.items():
            tot_actual = cls.compute_total(m_records, "actual_production_mt")
            avg_actual = cls.compute_average(m_records, "actual_production_mt") or 0.0
            tot_target = cls.compute_total(m_records, "target_mt")
            avg_avail = cls.compute_average(m_records, "equipment_or_face_availability_pct")

            achieve = None
            if tot_target and tot_target > 0:
                achieve = round((tot_actual / tot_target) * 100.0, 2)

            m_name = (mine_names_map or {}).get(m_code, m_code)

            items.append(
                MineComparisonItem(
                    mine_code=m_code,
                    mine_name=m_name,
                    total_production_mt=tot_actual,
                    avg_annual_production_mt=avg_actual,
                    target_mt=tot_target if tot_target > 0 else None,
                    achievement_pct=achieve,
                    avg_availability_pct=avg_avail,
                )
            )

        items.sort(key=lambda x: x.total_production_mt, reverse=True)
        return items
