from mesa.datacollection import DataCollector
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
import os


def build_datacollector(self) -> DataCollector:
        """Constructs and returns the Mesa DataCollector.

        Returns:
            A configured ``DataCollector`` instance covering model-level
            and agent-level reporters.
        """
        return DataCollector(
            model_reporters={
                # Fish stocks
                "stock_A": lambda m: m._region_stock_cache["A"],
                "stock_B": lambda m: m._region_stock_cache["B"],
                "stock_C": lambda m: m._region_stock_cache["C"],
                "stock_D": lambda m: m._region_stock_cache["D"],
                "total_stock": lambda m: m._region_stock_cache["TOTAL"],
                "stock_below_MSY_A": lambda m: (
                    1 if m._region_stock_cache["A"] < m.MSY_STOCK_A else 0
                ),
                "stock_below_MSY_B": lambda m: (
                    1 if m._region_stock_cache["B"] < m.MSY_STOCK_B else 0
                ),
                "stock_below_MSY_C": lambda m: (
                    1 if m._region_stock_cache["C"] < m.MSY_STOCK_C else 0
                ),
                "stock_below_MSY_D": lambda m: (
                    1 if m._region_stock_cache["D"] < m.MSY_STOCK_D else 0
                ),
                # Agent counts
                "num_agents": lambda m: m._daily_agent_metrics["num_agents"],
                "num_archipelago": lambda m: m._daily_agent_metrics[
                    "num_archipelago"
                ],
                "num_coastal": lambda m: m._daily_agent_metrics["num_coastal"],
                "num_trawler": lambda m: m._daily_agent_metrics["num_trawler"],
                "num_fishing": lambda m: m.num_fishing_midday,
                "num_at_home": lambda m: m.num_at_home_midday,
                "num_fished_today": lambda m: m.num_fished_today,
                "num_bankrupt": lambda m: m._daily_agent_metrics[
                    "num_bankrupt"
                ],
                # Catches
                "total_catch_daily": lambda m: m._daily_agent_metrics[
                    "total_catch_daily"
                ],
                "total_catch_cumulative": lambda m: m._daily_agent_metrics[
                    "total_catch_cumulative"
                ],
                "total_catch": lambda m: m.get_total_catch_all_agents(),
                "avg_catch_per_agent": lambda m: (
                    m._daily_agent_metrics["total_catch_cumulative"]
                    / m._daily_agent_metrics["num_agents"]
                    if m._daily_agent_metrics["num_agents"]
                    else 0
                ),
                "catch_region_A": lambda m: m._daily_agent_metrics[
                    "catch_region_A"
                ],
                "catch_region_B": lambda m: m._daily_agent_metrics[
                    "catch_region_B"
                ],
                "catch_region_C": lambda m: m._daily_agent_metrics[
                    "catch_region_C"
                ],
                "catch_region_D": lambda m: m._daily_agent_metrics[
                    "catch_region_D"
                ],
                # Economics
                "total_capital": lambda m: m._daily_agent_metrics[
                    "total_capital"
                ],
                "avg_capital": lambda m: m._daily_agent_metrics["avg_capital"],
                "median_capital": lambda m: m._daily_agent_metrics[
                    "median_capital"
                ],
                "min_capital": lambda m: m._daily_agent_metrics["min_capital"],
                "max_capital": lambda m: m._daily_agent_metrics["max_capital"],
                "total_profit": lambda m: m._daily_agent_metrics[
                    "total_profit"
                ],
                "avg_profit": lambda m: m._daily_agent_metrics["avg_profit"],
                "total_revenue": lambda m: m._daily_agent_metrics[
                    "total_revenue"
                ],
                "total_costs": lambda m: m._daily_agent_metrics["total_costs"],
                # Inequality
                "gini_capital": lambda m: m._daily_agent_metrics[
                    "gini_capital"
                ],
                "gini_wealth": lambda m: m._daily_agent_metrics["gini_wealth"],
                "gini_catch": lambda m: m._daily_agent_metrics["gini_catch"],
                # Activity
                "avg_days_at_sea": lambda m: m._daily_agent_metrics[
                    "avg_days_at_sea"
                ],
                "total_trips": lambda m: m._daily_agent_metrics["total_trips"],
                "avg_success_rate": lambda m: m._daily_agent_metrics[
                    "avg_success_rate"
                ],
                # Memory and perception
                "avg_growth_perception": lambda m: m._daily_agent_metrics[
                    "avg_growth_perception"
                ],
                "num_perceive_scarcity": lambda m: m._daily_agent_metrics[
                    "num_perceive_scarcity"
                ],
                "avg_memory_size": lambda m: m._daily_agent_metrics[
                    "avg_memory_size"
                ],
                # Weather and time
                "bad_weather": lambda m: 1 if m.bad_weather else 0,
                "current_step": lambda m: m.current_step,
                "current_year": lambda m: m.current_step // m.YEAR,
                "current_day_of_year": lambda m: m.current_step % m.YEAR,
            },
            agent_reporters={
                # Identity
                "step": lambda a: a.model.current_step,
                "unique_id": "unique_id",
                "fisher_type": "fisher_type",
                "age": "age",
                # Financial
                "capital": "capital",
                "wealth": "wealth",
                "total_profit": "total_profit",
                "total_revenue": "total_revenue",
                "total_cost": "total_cost",
                "bankrupt": "bankrupt",
                # Activity
                "total_catch": "total_catch",
                "days_at_sea": "days_at_sea",
                "profitable_trips": "profitable_trip",
                "unprofitable_trips": "unprofitable_trip",
                "at_home": "at_home",
                "gone_fishing": "gone_fishing",
                "fished_today": "fished_today",
                "at_sea": "at_sea",
                "current_location": lambda a: (
                    a.current_location if a.gone_fishing else (0, 0)
                ),
                "catch": lambda a: (
                    a.accumulated_catch if a.gone_fishing else 0
                ),
                # Decision-making
                "will_fish": "will_fish",
                "region_preference": "region_preference",
                "current_region": "current_region",
                "growth_perception": "growth_perception",
                "lay_low": "lay_low",
                # Memory
                "memory_size": lambda a: len(a.memory),
                "good_spots_count": lambda a: len(a.good_spots_memory),
            },
        )

def build_daily_agent_metrics_cache(self) -> None:
        """Computes and caches per-step aggregate metrics across all agents.

        Populates ``_daily_agent_metrics`` with totals, averages, Gini
        coefficients, and per-region catch breakdowns.
        """
        agents = list(self.agents)

        capitals: List[float] = []
        wealths: List[float] = []
        catches: List[float] = []
        profits: List[float] = []
        revenues: List[float] = []
        costs: List[float] = []
        days_at_sea: List[int] = []
        growth_perceptions: List[float] = []
        memory_sizes: List[int] = []

        by_type_count: Dict[str, int] = {
            "archipelago": 0, "coastal": 0, "trawler": 0
        }
        by_region_catch: Dict[str, float] = {
            "A": 0, "B": 0, "C": 0, "D": 0
        }

        num_bankrupt = 0
        total_catch_daily = 0.0
        total_catch_cumulative = 0.0
        total_capital = 0.0
        total_profit = 0.0
        total_revenue = 0.0
        total_costs = 0.0
        total_trips = 0
        num_perceive_scarcity = 0
        success_rate_sum = 0.0
        success_rate_count = 0
        min_capital: Optional[float] = None
        max_capital: Optional[float] = None

        for agent in agents:
            ftype = agent.fisher_type
            if ftype in by_type_count:
                by_type_count[ftype] += 1

            if agent.bankrupt:
                num_bankrupt += 1

            total_catch_daily += agent.accumulated_catch
            total_catch_cumulative += agent.total_catch
            total_capital += agent.capital
            total_profit += agent.total_profit
            total_revenue += agent.total_revenue
            total_costs += agent.total_cost

            capitals.append(agent.capital)
            wealths.append(agent.wealth)
            catches.append(agent.total_catch)
            profits.append(agent.total_profit)
            revenues.append(agent.total_revenue)
            costs.append(agent.total_cost)
            days_at_sea.append(agent.days_at_sea)
            growth_perceptions.append(agent.growth_perception)
            memory_sizes.append(len(agent.memory))

            if getattr(agent, "perceive_scarcity", False):
                num_perceive_scarcity += 1

            trips = agent.profitable_trip + agent.unprofitable_trip
            total_trips += trips
            if trips > 0:
                success_rate_sum += agent.profitable_trip / trips
                success_rate_count += 1

            if agent.current_region in by_region_catch:
                by_region_catch[agent.current_region] += (
                    agent.accumulated_catch
                )

            if min_capital is None or agent.capital < min_capital:
                min_capital = agent.capital
            if max_capital is None or agent.capital > max_capital:
                max_capital = agent.capital

        self._daily_agent_metrics = {
            "num_agents": len(agents),
            "num_archipelago": by_type_count["archipelago"],
            "num_coastal": by_type_count["coastal"],
            "num_trawler": by_type_count["trawler"],
            "num_bankrupt": num_bankrupt,
            "total_catch_daily": total_catch_daily,
            "total_catch_cumulative": total_catch_cumulative,
            "total_capital": total_capital,
            "avg_capital": self._safe_mean(capitals),
            "median_capital": self._safe_median(capitals),
            "min_capital": min_capital if min_capital is not None else 0,
            "max_capital": max_capital if max_capital is not None else 0,
            "total_profit": total_profit,
            "avg_profit": self._safe_mean(profits),
            "total_revenue": total_revenue,
            "total_costs": total_costs,
            "gini_capital": self.calculate_gini(capitals) if capitals else 0,
            "gini_wealth": self.calculate_gini(wealths) if wealths else 0,
            "gini_catch": self.calculate_gini(catches) if catches else 0,
            "avg_days_at_sea": self._safe_mean(days_at_sea),
            "total_trips": total_trips,
            "avg_success_rate": (
                success_rate_sum / success_rate_count
                if success_rate_count
                else 0
            ),
            "avg_growth_perception": self._safe_mean(growth_perceptions),
            "num_perceive_scarcity": num_perceive_scarcity,
            "avg_memory_size": self._safe_mean(memory_sizes),
            "catch_region_A": by_region_catch["A"],
            "catch_region_B": by_region_catch["B"],
            "catch_region_C": by_region_catch["C"],
            "catch_region_D": by_region_catch["D"],
        }

def append_daily_agent_rows_for_monthly_export(self) -> None:
        """Appends one row per agent to the monthly export buffer.

        Stores the current-step snapshot in ``_monthly_agent_rows`` to
        avoid reconstructing history from the DataCollector later.
        """
        step_value = self.current_step
        for agent in self.agents:
            self._monthly_agent_rows.append({
                "step": step_value,
                "unique_id": agent.unique_id,
                "fisher_type": agent.fisher_type,
                "age": agent.age,
                "capital": agent.capital,
                "wealth": agent.wealth,
                "total_profit": agent.total_profit,
                "total_revenue": agent.total_revenue,
                "total_cost": agent.total_cost,
                "bankrupt": agent.bankrupt,
                "total_catch": agent.total_catch,
                "days_at_sea": agent.days_at_sea,
                "profitable_trips": agent.profitable_trip,
                "unprofitable_trips": agent.unprofitable_trip,
                "at_home": agent.at_home,
                "gone_fishing": agent.gone_fishing,
                "fished_today": agent.fished_today,
                "at_sea": agent.at_sea,
                "current_location": (
                    agent.current_location if agent.gone_fishing else (0, 0)
                ),
                "catch": (
                    agent.accumulated_catch if agent.gone_fishing else 0
                ),
                "will_fish": agent.will_fish,
                "region_preference": agent.region_preference,
                "current_region": agent.current_region,
                "growth_perception": agent.growth_perception,
                "lay_low": agent.lay_low,
                "memory_size": len(agent.memory),
                "good_spots_count": len(agent.good_spots_memory),
            })

def export_monthly_agent_buffer(self) -> None:
        """Flushes the monthly agent buffer to a CSV file and clears it.

        Writes to ``./results/biomass/agent_<step>.csv``. Does nothing
        if the buffer is empty.
        """
        if not self._monthly_agent_rows:
            return

        os.makedirs("./results/biomass", exist_ok=True)
        df = pd.DataFrame(self._monthly_agent_rows)
        output_path = os.path.join(
            "./results/biomass", f"agent_{self.current_step}.csv"
        )
        df.to_csv(output_path, index=False)

        if self.verbose:
            print(
                f"Exported: agent_{self.current_step}.csv"
                f" ({len(df)} rows)"
            )

        self._monthly_agent_rows.clear()

def collect_yearly_data(self) -> Dict[str, Any]:
        """Collects a detailed yearly snapshot and appends it to ``yearly_data``.

        Returns:
            Dictionary containing year, step, regional stocks, agent
            counts, catch totals, economic totals, Gini coefficients,
            and activity metrics.
        """
        year = self.current_step // self.YEAR

        stock_a = self._region_stock_cache["A"]
        stock_b = self._region_stock_cache["B"]
        stock_c = self._region_stock_cache["C"]
        stock_d = self._region_stock_cache["D"]
        total_stock = self._region_stock_cache["TOTAL"]

        by_type_count: Dict[str, int] = {
            "archipelago": 0, "coastal": 0, "trawler": 0
        }
        by_type_total_catch: Dict[str, float] = {
            "archipelago": 0.0, "coastal": 0.0, "trawler": 0.0
        }
        by_type_capitals: Dict[str, List[float]] = {
            "archipelago": [], "coastal": [], "trawler": []
        }

        capitals: List[float] = []
        wealths: List[float] = []
        catches: List[float] = []
        days_at_sea_list: List[int] = []

        total_capital = 0.0
        total_profit = 0.0
        total_revenue = 0.0
        total_costs = 0.0
        total_trips = 0
        total_profitable_trips = 0
        total_unprofitable_trips = 0
        success_rate_sum = 0.0
        success_rate_count = 0
        num_bankrupt = 0
        num_agents = 0

        for agent in self.agents:
            num_agents += 1
            ftype = agent.fisher_type

            if ftype in by_type_count:
                by_type_count[ftype] += 1
                by_type_total_catch[ftype] += agent.total_catch
                by_type_capitals[ftype].append(agent.capital)

            capitals.append(agent.capital)
            wealths.append(agent.wealth)
            catches.append(agent.total_catch)
            days_at_sea_list.append(agent.days_at_sea)

            total_capital += agent.capital
            total_profit += agent.total_profit
            total_revenue += agent.total_revenue
            total_costs += agent.total_cost

            total_profitable_trips += agent.profitable_trip
            total_unprofitable_trips += agent.unprofitable_trip
            trips = agent.profitable_trip + agent.unprofitable_trip
            total_trips += trips
            if trips > 0:
                success_rate_sum += agent.profitable_trip / trips
                success_rate_count += 1

            if agent.bankrupt:
                num_bankrupt += 1

        yearly_summary: Dict[str, Any] = {
            "year": year,
            "step": self.current_step,
            "stock_A": stock_a,
            "stock_B": stock_b,
            "stock_C": stock_c,
            "stock_D": stock_d,
            "total_stock": total_stock,
            "stock_A_pct_K": (
                stock_a / self.CARRYING_CAPACITY_A
                if self.CARRYING_CAPACITY_A > 0
                else 0
            ),
            "stock_B_pct_K": (
                stock_b / self.CARRYING_CAPACITY_B
                if self.CARRYING_CAPACITY_B > 0
                else 0
            ),
            "stock_C_pct_K": (
                stock_c / self.CARRYING_CAPACITY_C
                if self.CARRYING_CAPACITY_C > 0
                else 0
            ),
            "stock_D_pct_K": (
                stock_d / self.CARRYING_CAPACITY_D
                if self.CARRYING_CAPACITY_D > 0
                else 0
            ),
            "num_agents": num_agents,
            "num_archipelago": by_type_count["archipelago"],
            "num_coastal": by_type_count["coastal"],
            "num_trawler": by_type_count["trawler"],
            "num_bankrupt": num_bankrupt,
            "total_catch_archipelago": by_type_total_catch["archipelago"],
            "total_catch_coastal": by_type_total_catch["coastal"],
            "total_catch_trawler": by_type_total_catch["trawler"],
            "total_catch_all": sum(catches),
            "avg_catch_archipelago": (
                by_type_total_catch["archipelago"]
                / by_type_count["archipelago"]
                if by_type_count["archipelago"]
                else 0
            ),
            "avg_catch_coastal": (
                by_type_total_catch["coastal"] / by_type_count["coastal"]
                if by_type_count["coastal"]
                else 0
            ),
            "avg_catch_trawler": (
                by_type_total_catch["trawler"] / by_type_count["trawler"]
                if by_type_count["trawler"]
                else 0
            ),
            "avg_capital_archipelago": self._safe_mean(
                by_type_capitals["archipelago"]
            ),
            "avg_capital_coastal": self._safe_mean(
                by_type_capitals["coastal"]
            ),
            "avg_capital_trawler": self._safe_mean(
                by_type_capitals["trawler"]
            ),
            "total_capital": total_capital,
            "total_profit": total_profit,
            "total_revenue": total_revenue,
            "total_costs": total_costs,
            "gini_capital": self.calculate_gini(capitals) if capitals else 0,
            "gini_wealth": self.calculate_gini(wealths) if wealths else 0,
            "gini_catch": self.calculate_gini(catches) if catches else 0,
            "total_trips": total_trips,
            "total_profitable_trips": total_profitable_trips,
            "total_unprofitable_trips": total_unprofitable_trips,
            "avg_success_rate": (
                success_rate_sum / success_rate_count
                if success_rate_count
                else 0
            ),
            "avg_days_at_sea": self._safe_mean(days_at_sea_list),
        }

        self.yearly_data.append(yearly_summary)
        return yearly_summary

def get_total_catch_all_agents(self) -> float:
        """Returns total catch since the last annual snapshot.

        Returns:
            Sum of incremental catches relative to ``last_year_catches``,
            or the raw cumulative total if no snapshot exists yet.
        """
        if not getattr(self, "last_year_catches", None):
            return sum(a.total_catch for a in self.agents)

        current_catches = {
            a.unique_id: a.total_catch for a in self.agents
        }
        return sum(
            current_catches[aid] - self.last_year_catches.get(aid, 0)
            for aid in current_catches
        )

def safe_mean(self, values: List[float]) -> float:
    """Returns the arithmetic mean of a list, or 0 if empty.

    Args:
        values: Numeric list to average.

    Returns:
        Mean value, or 0.0 for an empty list.
    """
    if not values:
        return 0.0
    return sum(values) / len(values)

def safe_median(self, values: List[float]) -> float:
    """Returns the median of a list, or 0 if empty.

    Args:
        values: Numeric list.

    Returns:
        Median value, or 0.0 for an empty list.
    """
    if not values:
        return 0.0
    sorted_values = sorted(values)
    mid = len(sorted_values) // 2
    if len(sorted_values) % 2 == 0:
        return (sorted_values[mid - 1] + sorted_values[mid]) / 2
    return sorted_values[mid]

def calculate_gini(self, values: List[float]) -> float:
    """Calculates the Gini coefficient for a distribution.

    Args:
        values: Non-negative numeric list (capital, wealth, catch,
            etc.). Negative values are clamped to 0.

    Returns:
        Gini coefficient in [0, 1] where 0 is perfect equality and
        1 is perfect inequality. Returns 0 for empty or all-zero
        lists.
    """
    if not values:
        return 0.0

    clamped = [max(0.0, v) for v in values]
    total = sum(clamped)
    if total == 0:
        return 0.0

    sorted_values = sorted(clamped)
    num = len(sorted_values)
    cumsum = sum((i + 1) * v for i, v in enumerate(sorted_values))
    return (2 * cumsum) / (num * total) - (num + 1) / num