from mesa.datacollection import DataCollector
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
import os


def build_datacollector(self) -> DataCollector:
        return DataCollector(
            model_reporters={
                "total_stock": lambda m: m._region_stock_cache["TOTAL"],
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
                "num_retired": lambda m: m._daily_agent_metrics.get(
                    "num_retired", 0
                ),
                "num_retired_archipelago": lambda m: m._daily_agent_metrics.get(
                    "num_retired_archipelago", 0
                ),
                "num_retired_coastal": lambda m: m._daily_agent_metrics.get(
                    "num_retired_coastal", 0
                ),
                "num_retired_trawler": lambda m: m._daily_agent_metrics.get(
                    "num_retired_trawler", 0
                ),
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
                "gini_capital": lambda m: m._daily_agent_metrics[
                    "gini_capital"
                ],
                "gini_wealth": lambda m: m._daily_agent_metrics["gini_wealth"],
                "gini_catch": lambda m: m._daily_agent_metrics["gini_catch"],
                "avg_days_at_sea": lambda m: m._daily_agent_metrics[
                    "avg_days_at_sea"
                ],
                "total_trips": lambda m: m._daily_agent_metrics["total_trips"],
                "avg_success_rate": lambda m: m._daily_agent_metrics[
                    "avg_success_rate"
                ],
                "avg_growth_perception": lambda m: m._daily_agent_metrics[
                    "avg_growth_perception"
                ],
                "num_perceive_scarcity": lambda m: m._daily_agent_metrics[
                    "num_perceive_scarcity"
                ],
                "avg_memory_size": lambda m: m._daily_agent_metrics[
                    "avg_memory_size"
                ],
                "bad_weather": lambda m: 1 if m.bad_weather else 0,
                "current_step": lambda m: m.current_step,
                "current_year": lambda m: m.current_step // m.YEAR,
                "current_day_of_year": lambda m: m.current_step % m.YEAR,
            },
            agent_reporters={
                "step": lambda a: a.model.current_step,
                "unique_id": "unique_id",
                "fisher_type": "fisher_type",
                "age": "age",
                "capital": "capital",
                "wealth": "wealth",
                "total_profit": "total_profit",
                "total_revenue": "total_revenue",
                "total_cost": "total_cost",
                "bankrupt": "bankrupt",
                "retired": "retired",
                "retired_at": lambda a: getattr(a, "retired_at_step", None),
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
                "will_fish": "will_fish",
                "growth_perception": "growth_perception",
                "lay_low": "lay_low",
                "memory_size": lambda a: len(a.memory),
                "good_spots_count": lambda a: len(a.good_spots_memory),
            },
        )

def build_daily_agent_metrics_cache(self) -> None:
        agents = list(self.agents)
        # For model-level reporters we count only active agents (retired excluded).
        # Retired stats are kept separately in model._retired_agents.
        num_retired = len(getattr(self, "_retired_agents", []))

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
            "num_retired": num_retired,
            "num_retired_archipelago": sum(1 for a in getattr(self, "_retired_agents", []) if a.fisher_type == "archipelago"),
            "num_retired_coastal": sum(1 for a in getattr(self, "_retired_agents", []) if a.fisher_type == "coastal"),
            "num_retired_trawler": sum(1 for a in getattr(self, "_retired_agents", []) if a.fisher_type == "trawler"),
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
        }

def append_daily_agent_rows_for_monthly_export(self) -> None:
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
                "retired": getattr(agent, "retired", False),
                "retired_at": getattr(agent, "retired_at_step", None),
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
                "growth_perception": agent.growth_perception,
                "lay_low": agent.lay_low,
                "memory_size": len(agent.memory),
                "good_spots_count": len(agent.good_spots_memory),
            })

def export_monthly_agent_buffer(self) -> None:
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

def export_monthly_fishing_mortality(self) -> None:
        monthly_catch = getattr(self, "monthly_catch_by_flotilla", None)
        if monthly_catch is None:
            return

        month_start_biomass = getattr(self, "month_start_biomass", None)
        if month_start_biomass is None:
            month_start_biomass = self.species_biomass

        os.makedirs("./results/biomass", exist_ok=True)
        output_path = os.path.join(
            "./results/biomass", f"F_{self.current_step}.csv"
        )

        rows: List[str] = ["ligne;colonne;flottille;espèce;F"]
        for f_idx in sorted(set(self.flotilla_indices.values())):
            for y in range(monthly_catch.shape[1]):
                for x in range(monthly_catch.shape[2]):
                    biomass_vec = month_start_biomass[y, x, :]
                    catch_vec = monthly_catch[f_idx, y, x, :]
                    for s_idx, catch in enumerate(catch_vec):
                        if catch <= 0.0:
                            continue
                        biomass = biomass_vec[s_idx]
                        if biomass <= 0.0:
                            continue
                        f_value = catch / biomass
                        rows.append(
                            f"{y + 1};{x + 1};{f_idx};"
                            f"{self.species_names[s_idx]};{float(f_value):.10g}"
                        )

        tmp_path = output_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write("\n".join(rows) + "\n")
        os.replace(tmp_path, output_path)

        if self.verbose:
            print(
                f"Exported: F_{self.current_step}.csv"
                f" ({len(rows) - 1} rows)"
            )

        self.month_start_biomass = self.species_biomass.copy()
        monthly_catch.fill(0.0)

def collect_yearly_data(self) -> Dict[str, Any]:
        year = self.current_step // self.YEAR

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

        # Retired archive (definitive, never reused) - keep for final stats
        retired_agents = getattr(self, "_retired_agents", [])
        num_retired = len(retired_agents)
        retired_catch = sum(a.total_catch for a in retired_agents)
        retired_capital = sum(a.capital for a in retired_agents)

        yearly_summary: Dict[str, Any] = {
            "year": year,
            "step": self.current_step,
            "total_stock": total_stock,
            "num_agents": num_agents,  # active only
            "num_archipelago": by_type_count["archipelago"],
            "num_coastal": by_type_count["coastal"],
            "num_trawler": by_type_count["trawler"],
            "num_bankrupt": num_bankrupt,
            "num_retired": num_retired,
            "num_retired_archipelago": sum(1 for a in retired_agents if a.fisher_type == "archipelago"),
            "num_retired_coastal": sum(1 for a in retired_agents if a.fisher_type == "coastal"),
            "num_retired_trawler": sum(1 for a in retired_agents if a.fisher_type == "trawler"),
            "total_catch_retired": retired_catch,
            "total_catch_all_including_retired": sum(catches) + retired_catch,
            "total_capital_retired": retired_capital,
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
        # Cumulative catch including retired (for total_catch metric)
        # If last_year_catches is empty (first year), sum all.
        if not getattr(self, "last_year_catches", None):
            return sum(a.total_catch for a in self.agents) + sum(a.total_catch for a in getattr(self, "_retired_agents", []))

        current_catches = {
            a.unique_id: a.total_catch for a in self.agents
        }
        # Include retired catches in yearly delta (they are frozen)
        for a in getattr(self, "_retired_agents", []):
            current_catches[a.unique_id] = a.total_catch
        return sum(
            current_catches[aid] - self.last_year_catches.get(aid, 0)
            for aid in current_catches
        )

def safe_mean(self, values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)

def safe_median(self, values: List[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    mid = len(sorted_values) // 2
    if len(sorted_values) % 2 == 0:
        return (sorted_values[mid - 1] + sorted_values[mid]) / 2
    return sorted_values[mid]

def calculate_gini(self, values: List[float]) -> float:
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
