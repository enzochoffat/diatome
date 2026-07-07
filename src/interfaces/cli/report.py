from typing import Dict, List, Any


def print_final_summary(self) -> None:
    """Prints a comprehensive summary at the end of the simulation."""


    stock_a = self._region_stock_cache.get("A", 0)
    stock_b = self._region_stock_cache.get("B", 0)
    stock_c = self._region_stock_cache.get("C", 0)
    stock_d = self._region_stock_cache.get("D", 0)
    total_stock = self._region_stock_cache.get("TOTAL", 0)
    agents_list = list(self.agents)

    print(
        f"\nDuration: {self.current_step} days"
        f" ({self.current_step / self.YEAR:.1f} years)"
    )
    print(f"Agents: {len(agents_list)} total")

    print("\n--- FISH STOCKS ---")
    for label, stock, capacity in (
        ("A", stock_a, self.CARRYING_CAPACITY_A),
        ("B", stock_b, self.CARRYING_CAPACITY_B),
        ("C", stock_c, self.CARRYING_CAPACITY_C),
        ("D", stock_d, self.CARRYING_CAPACITY_D),
    ):
        pct = stock / capacity if capacity > 0 else 0
        print(
            f"Region {label}: {stock:>10,.0f} / {capacity:,.0f}"
            f" ({pct:.1%})"
        )
    print(f"TOTAL:    {total_stock:>10,.0f}")

    print("\n--- ECONOMICS ---")
    total_catch = sum(a.total_catch for a in agents_list)
    total_capital = sum(a.capital for a in agents_list)
    total_profit = sum(a.total_profit for a in agents_list)
    print(f"Total catch:   {total_catch:>12,.0f}")
    print(f"Total capital: {total_capital:>12,.2f}")
    print(f"Total profit:  {total_profit:>12,.2f}")
    avg_cap = total_capital / len(agents_list) if agents_list else 0
    print(f"Avg capital:   {avg_cap:>12,.2f}")

    print("\n--- INEQUALITY ---")
    print(
        f"Gini capital: "
        f"{self.calculate_gini([a.capital for a in agents_list]) if agents_list else 0:.3f}"
    )
    print(
        f"Gini wealth:  "
        f"{self.calculate_gini([a.wealth for a in agents_list]) if agents_list else 0:.3f}"
    )
    print(
        f"Gini catch:   "
        f"{self.calculate_gini([a.total_catch for a in agents_list]) if agents_list else 0:.3f}"
    )

    print("\n--- BY FISHER TYPE ---")
    by_type: Dict[str, List[Any]] = {
        "archipelago": [], "coastal": [], "trawler": []
    }
    for agent in agents_list:
        if agent.fisher_type in by_type:
            by_type[agent.fisher_type].append(agent)

    for ftype in ("archipelago", "coastal", "trawler"):
        type_agents = by_type[ftype]
        if type_agents:
            avg_catch = (
                sum(a.total_catch for a in type_agents)
                / len(type_agents)
            )
            avg_capital = (
                sum(a.capital for a in type_agents) / len(type_agents)
            )
            bankrupt = sum(1 for a in type_agents if a.bankrupt)
            print(
                f"{ftype:>12}: {len(type_agents):>3} agents,"
                f" avg catch={avg_catch:>8,.0f},"
                f" avg capital={avg_capital:>8,.2f},"
                f" bankrupt={bankrupt}"
            )

    print("=" * 80 + "\n")