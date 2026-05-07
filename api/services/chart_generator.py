"""
Chart Generator Service for LaTeX-based PDF reporting.

Generates matplotlib-based charts for embedding in PDF reports:
- Relationship network diagrams
- Timeline charts
- Entity type distribution charts
- Activity heatmaps
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import networkx as nx
from matplotlib.figure import Figure

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Generate charts for embedding in LaTeX reports."""

    def __init__(self, dpi: int = 150, format: str = "pdf"):
        """
        Initialize chart generator.

        Args:
            dpi: Resolution for saved images
            format: Output format ('pdf' or 'png')
        """
        self.dpi = dpi
        self.format = format
        self.temp_dir = Path(tempfile.gettempdir()) / "basset_charts"
        self.temp_dir.mkdir(exist_ok=True)

    def relationship_network_chart(
        self, entities: List[Dict[str, Any]], relationships: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a relationship network diagram.

        Args:
            entities: List of entity dicts with 'id' and 'name'
            relationships: List of relationship dicts with 'source', 'target', 'type'

        Returns:
            Path to saved PDF/PNG image
        """
        try:
            fig, ax = plt.subplots(figsize=(12, 10))

            # Create graph
            G = nx.DiGraph()

            # Add nodes
            for entity in entities:
                G.add_node(entity["id"], name=entity.get("name", entity["id"]))

            # Add edges
            for rel in relationships:
                if rel.get("source") in [e["id"] for e in entities] and rel.get(
                    "target"
                ) in [e["id"] for e in entities]:
                    G.add_edge(
                        rel["source"], rel["target"], type=rel.get("type", "connected")
                    )

            # Layout
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

            # Draw
            nx.draw_networkx_nodes(
                G,
                pos,
                node_color="lightblue",
                node_size=3000,
                ax=ax,
                edgecolors="navy",
                linewidths=2,
            )

            nx.draw_networkx_edges(G, pos, ax=ax, edge_color="gray", arrows=True)

            # Labels
            labels = {
                node: G.nodes[node].get("name", node)[:20] for node in G.nodes()
            }
            nx.draw_networkx_labels(G, pos, labels, font_size=9, ax=ax)

            ax.set_title("Entity Relationship Network", fontsize=16, fontweight="bold")
            ax.axis("off")
            plt.tight_layout()

            # Save
            output_path = self.temp_dir / f"network_{id(G)}.{self.format}"
            plt.savefig(str(output_path), dpi=self.dpi, format=self.format, bbox_inches="tight")
            plt.close(fig)

            logger.info(f"Generated network chart: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to generate network chart: {e}")
            raise

    def timeline_chart(
        self, events: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a timeline chart.

        Args:
            events: List of event dicts with 'date' (datetime) and 'description'

        Returns:
            Path to saved PDF/PNG image
        """
        try:
            if not events:
                return self._create_empty_chart("No timeline events")

            # Sort events by date
            sorted_events = sorted(
                events, key=lambda x: x.get("date", ""), reverse=True
            )

            fig, ax = plt.subplots(figsize=(14, 8))

            # Extract dates and descriptions
            dates = []
            descriptions = []
            for event in sorted_events:
                try:
                    import datetime

                    date = event.get("date")
                    if isinstance(date, str):
                        date = datetime.datetime.fromisoformat(date)
                    dates.append(date)
                    descriptions.append(
                        event.get("description", "No description")[:50]
                    )
                except Exception:
                    continue

            if not dates:
                return self._create_empty_chart("No valid timeline events")

            # Create timeline
            y_positions = range(len(dates))
            ax.scatter(dates, y_positions, s=200, color="steelblue", zorder=3)

            # Add vertical line
            ax.plot(dates, y_positions, "gray", linestyle="--", linewidth=1, zorder=1)

            # Labels
            ax.set_yticks(y_positions)
            ax.set_yticklabels(descriptions, fontsize=9)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

            ax.set_xlabel("Date", fontsize=12, fontweight="bold")
            ax.set_title("Investigation Timeline", fontsize=16, fontweight="bold")
            ax.grid(axis="x", alpha=0.3)
            plt.tight_layout()

            # Save
            output_path = self.temp_dir / f"timeline_{id(dates)}.{self.format}"
            plt.savefig(str(output_path), dpi=self.dpi, format=self.format, bbox_inches="tight")
            plt.close(fig)

            logger.info(f"Generated timeline chart: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to generate timeline chart: {e}")
            raise

    def entity_distribution_chart(
        self, entity_types: Dict[str, int]
    ) -> str:
        """
        Generate entity type distribution pie/bar chart.

        Args:
            entity_types: Dict of {entity_type: count}

        Returns:
            Path to saved PDF/PNG image
        """
        try:
            if not entity_types:
                return self._create_empty_chart("No entity distribution data")

            fig, ax = plt.subplots(figsize=(10, 8))

            types = list(entity_types.keys())
            counts = list(entity_types.values())

            # Use bar chart for clarity
            colors = plt.cm.Set3(range(len(types)))
            bars = ax.bar(types, counts, color=colors, edgecolor="navy", linewidth=2)

            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{int(height)}",
                    ha="center",
                    va="bottom",
                    fontweight="bold",
                )

            ax.set_ylabel("Count", fontsize=12, fontweight="bold")
            ax.set_xlabel("Entity Type", fontsize=12, fontweight="bold")
            ax.set_title("Entity Type Distribution", fontsize=16, fontweight="bold")
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
            plt.tight_layout()

            # Save
            output_path = self.temp_dir / f"distribution_{id(entity_types)}.{self.format}"
            plt.savefig(str(output_path), dpi=self.dpi, format=self.format, bbox_inches="tight")
            plt.close(fig)

            logger.info(f"Generated distribution chart: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to generate distribution chart: {e}")
            raise

    def activity_heatmap(
        self, activity_timeline: Dict[str, int]
    ) -> str:
        """
        Generate activity heatmap (activity by day/hour).

        Args:
            activity_timeline: Dict of {date_str: activity_count}

        Returns:
            Path to saved PDF/PNG image
        """
        try:
            if not activity_timeline:
                return self._create_empty_chart("No activity data")

            fig, ax = plt.subplots(figsize=(12, 6))

            dates = sorted(activity_timeline.keys())
            activities = [activity_timeline[d] for d in dates]

            # Create heatmap using bar colors
            colors = plt.cm.YlOrRd(
                [a / (max(activities) + 1) if max(activities) > 0 else 0 for a in activities]
            )

            bars = ax.bar(range(len(dates)), activities, color=colors, edgecolor="black", linewidth=1)

            # Add value labels
            for i, bar in enumerate(bars):
                height = bar.get_height()
                if height > 0:
                    ax.text(
                        i,
                        height,
                        f"{int(height)}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                    )

            ax.set_xticks(range(0, len(dates), max(1, len(dates) // 10)))
            ax.set_xticklabels(
                [dates[i] for i in range(0, len(dates), max(1, len(dates) // 10))],
                rotation=45,
                ha="right",
            )

            ax.set_ylabel("Activity Count", fontsize=12, fontweight="bold")
            ax.set_xlabel("Date", fontsize=12, fontweight="bold")
            ax.set_title("Activity Heatmap Over Time", fontsize=16, fontweight="bold")
            ax.grid(axis="y", alpha=0.3)
            plt.tight_layout()

            # Save
            output_path = self.temp_dir / f"heatmap_{id(activity_timeline)}.{self.format}"
            plt.savefig(str(output_path), dpi=self.dpi, format=self.format, bbox_inches="tight")
            plt.close(fig)

            logger.info(f"Generated heatmap: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to generate heatmap: {e}")
            raise

    def _create_empty_chart(self, message: str) -> str:
        """Create a placeholder chart when no data is available."""
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            fontsize=14,
            color="gray",
            transform=ax.transAxes,
        )
        ax.axis("off")
        plt.tight_layout()

        output_path = self.temp_dir / f"empty_{id(message)}.{self.format}"
        plt.savefig(str(output_path), dpi=self.dpi, format=self.format, bbox_inches="tight")
        plt.close(fig)

        return str(output_path)

    def cleanup(self):
        """Clean up temporary chart files."""
        try:
            import shutil

            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up chart directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup chart directory: {e}")
