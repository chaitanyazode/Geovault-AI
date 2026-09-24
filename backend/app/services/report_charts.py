"""
GeoVault AI - Report Chart Generation Service (Phase 6B)
Headless matplotlib visualization engine producing high-resolution PNG charts
for embedded DOCX and PDF mining/operational reports.
"""

import os
import logging
from typing import List, Dict, Any, Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless Docker / server environments
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

logger = logging.getLogger("geovault.report_charts")


class ReportChartGenerator:
    """Generates publication-quality charts for executive and operational reports."""

    def __init__(self, charts_dir: str = "/data/reports/charts"):
        self.charts_dir = charts_dir
        os.makedirs(self.charts_dir, exist_ok=True)

    def generate_production_trend_chart(
        self,
        production_data: List[Dict[str, Any]],
        mine_code: str,
        output_filename: str
    ) -> Optional[str]:
        """
        Renders a publication-grade grouped bar chart for Coal Production (MT)
        and Target / Overburden Removal over the last 5 years, mirroring Section 3
        of the official CMPDI / CIL Annual Performance Report.
        """
        if not production_data:
            return None

        import numpy as np

        # Filter and sort by year
        valid_points = [
            p for p in production_data 
            if p.get("year") is not None and (
                p.get("actual_production_mt") is not None or 
                p.get("actual_raw_coal_production_mt") is not None or 
                p.get("actual_mt") is not None
            )
        ]
        if not valid_points:
            return None

        valid_points.sort(key=lambda x: x.get("year", 0))
        # Keep up to last 5 years
        if len(valid_points) > 5:
            valid_points = valid_points[-5:]

        years = [p.get("year") for p in valid_points]
        year_labels = [f"FY{y-1}-{str(y)[-2:]}" if y > 2000 else f"FY{y}" for y in years]

        actuals = [
            float(p.get("actual_production_mt") or p.get("actual_raw_coal_production_mt") or p.get("actual_mt") or 0.0)
            for p in valid_points
        ]
        targets = [
            float(p.get("target_mt") or p.get("target_raw_coal_production_mt") or 0.0)
            for p in valid_points
        ]

        # Check if actual OBR exists, otherwise use Target
        obrs = [
            float(p.get("actual_obr_mm3") or (actuals[i] * 3.67 if actuals[i] > 0 else 0.0))
            for i, p in enumerate(valid_points)
        ]
        has_targets = any(t > 0 for t in targets)

        output_path = os.path.join(self.charts_dir, output_filename)
        fig, ax = plt.subplots(figsize=(7.5, 3.4), dpi=180)

        try:
            # Clean institutional styling
            fig.patch.set_facecolor("#FFFFFF")
            ax.set_facecolor("#FFFFFF")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color("#94A3B8")
            ax.spines["bottom"].set_color("#94A3B8")
            ax.grid(True, axis="y", linestyle="--", alpha=0.6, color="#E2E8F0", zorder=1)

            x = np.arange(len(years))
            width = 0.32

            # Series 1: Coal Production (Dark Navy)
            bars1 = ax.bar(
                x - width / 2, actuals, width,
                label="Coal Production (MT)", color="#1A365D", zorder=3
            )

            # Series 2: Target or Overburden (Soft Blue)
            label2 = "Target (MT)" if has_targets else "Overburden (MCM)"
            vals2 = targets if has_targets else obrs
            bars2 = ax.bar(
                x + width / 2, vals2, width,
                label=label2, color="#60A5FA", zorder=3
            )

            # Bar Value Annotations
            for bar in bars1:
                h = bar.get_height()
                if h > 0:
                    ax.annotate(
                        f"{h:.2f}",
                        xy=(bar.get_x() + bar.get_width() / 2, h),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=8, fontweight="bold",
                        color="#0F172A"
                    )

            for bar in bars2:
                h = bar.get_height()
                if h > 0:
                    ax.annotate(
                        f"{h:.2f}",
                        xy=(bar.get_x() + bar.get_width() / 2, h),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=8,
                        color="#334155"
                    )

            # Title & Axis Styling
            ax.set_title(
                f"Production Performance Trend — {mine_code}",
                fontsize=10.5, fontweight="bold", pad=10, color="#1A365D", loc="left"
            )
            ax.set_xticks(x)
            ax.set_xticklabels(year_labels, fontsize=8.5, fontweight="bold", color="#334155")
            ax.set_ylabel("Quantity (Million Tonnes)", fontsize=8, fontweight="bold", color="#475569", labelpad=6)
            ax.tick_params(axis="y", labelsize=8, colors="#64748B")
            ax.tick_params(axis="x", length=0)

            # Legend
            ax.legend(
                frameon=True, facecolor="#FFFFFF", edgecolor="#E2E8F0",
                loc="upper left", fontsize=8, ncol=2
            )

            # Adjust margins
            plt.tight_layout()
            fig.savefig(output_path, dpi=180, facecolor=fig.get_facecolor(), bbox_inches="tight")
            logger.info(f"Production trend chart generated: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to generate production trend chart: {e}")
            return None
        finally:
            plt.close(fig)

    def generate_comparison_chart(
        self,
        comparisons: List[Dict[str, Any]],
        output_filename: str,
        year: Optional[int] = None
    ) -> Optional[str]:
        """
        Renders a bar chart comparing performance metrics across authorized mines.
        """
        if not comparisons or len(comparisons) < 2:
            return None

        output_path = os.path.join(self.charts_dir, output_filename)
        fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)

        try:
            mines = [c.get("mine_code", "Unknown") for c in comparisons]
            actuals = [float(c.get("actual_production_mt") or 0.0) for c in comparisons]
            targets = [float(c.get("target_production_mt") or 0.0) for c in comparisons]

            import numpy as np
            x = np.arange(len(mines))
            width = 0.35

            fig.patch.set_facecolor("#FFFFFF")
            ax.set_facecolor("#F8FAFC")
            ax.grid(True, linestyle="--", alpha=0.5, color="#CBD5E1", zorder=1)

            rects1 = ax.bar(x - width/2, actuals, width, label="Actual (MT)", color="#2563EB", zorder=2)
            rects2 = ax.bar(x + width/2, targets, width, label="Target (MT)", color="#F59E0B", zorder=2)

            # Value labels on bars
            for rect in rects1:
                h = rect.get_height()
                if h > 0:
                    ax.annotate(f"{h:.2f}",
                                xy=(rect.get_x() + rect.get_width() / 2, h),
                                xytext=(0, 3), textcoords="offset points",
                                ha="center", va="bottom", fontsize=8, fontweight="bold")

            for rect in rects2:
                h = rect.get_height()
                if h > 0:
                    ax.annotate(f"{h:.2f}",
                                xy=(rect.get_x() + rect.get_width() / 2, h),
                                xytext=(0, 3), textcoords="offset points",
                                ha="center", va="bottom", fontsize=8, fontweight="bold")

            yr_str = f" ({year})" if year else ""
            ax.set_title(f"Mine Performance Comparison{yr_str}", fontsize=12, fontweight="bold", pad=12, color="#0F172A")
            ax.set_ylabel("Production (Million Tonnes)", fontsize=10, fontweight="bold", color="#334155")
            ax.set_xticks(x)
            ax.set_xticklabels(mines, fontsize=10, fontweight="bold")
            ax.legend(frameon=True, facecolor="#FFFFFF", edgecolor="#E2E8F0", loc="upper right", fontsize=9)

            plt.tight_layout()
            fig.savefig(output_path, dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight")
            logger.info(f"Comparison chart generated: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to generate comparison chart: {e}")
            return None
        finally:
            plt.close(fig)

    def generate_dispatch_trend_chart(
        self,
        dispatch_data: List[Dict[str, Any]],
        mine_code: str,
        output_filename: str
    ) -> Optional[str]:
        """
        Renders dispatch performance across transport modes or fiscal years.
        """
        if not dispatch_data:
            return None

        output_path = os.path.join(self.charts_dir, output_filename)
        fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)

        try:
            fig.patch.set_facecolor("#FFFFFF")
            ax.set_facecolor("#F8FAFC")
            ax.grid(True, linestyle="--", alpha=0.5, color="#CBD5E1", zorder=1)

            years = [d.get("year") for d in dispatch_data if d.get("year")]
            dispatches = [float(d.get("dispatch_mt") or d.get("total_dispatch_mt") or 0.0) for d in dispatch_data]
            rail_dispatch = [float(d.get("rail_dispatch_mt") or 0.0) for d in dispatch_data]
            road_dispatch = [float(d.get("road_dispatch_mt") or 0.0) for d in dispatch_data]

            if years and (any(r > 0 for r in rail_dispatch) or any(rd > 0 for rd in road_dispatch)):
                ax.bar(years, rail_dispatch, label="Rail Dispatch (MT)", color="#059669", zorder=2)
                ax.bar(years, road_dispatch, bottom=rail_dispatch, label="Road Dispatch (MT)", color="#0D9488", zorder=2)
                ax.set_xlabel("Reporting Year", fontsize=10, fontweight="bold", color="#334155")
            elif years and any(d > 0 for d in dispatches):
                ax.bar(years, dispatches, label="Dispatch (MT)", color="#0D9488", zorder=2, width=0.45)
                ax.set_xlabel("Reporting Year", fontsize=10, fontweight="bold", color="#334155")
            else:
                return None

            ax.set_title(f"Dispatch Performance — {mine_code}", fontsize=12, fontweight="bold", pad=12, color="#0F172A")
            ax.set_ylabel("Quantity Dispatched (MT)", fontsize=10, fontweight="bold", color="#334155")
            ax.legend(frameon=True, facecolor="#FFFFFF", edgecolor="#E2E8F0", loc="upper left", fontsize=9)

            plt.tight_layout()
            fig.savefig(output_path, dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight")
            return output_path
        except Exception as e:
            logger.error(f"Failed to generate dispatch trend chart: {e}")
            return None
        finally:
            plt.close(fig)
