from typing import Dict, Any


def calculate_profit(agent, catch: float, costs: float) -> Dict[str, Any]:
    revenue = catch * agent.model.FISH_PRICE
    profit = revenue - costs

    return {
        "revenue": revenue,
        "costs": costs,
        "profit": profit,
        "catch": catch,
        "price_per_unit": agent.model.FISH_PRICE,
        "location": None,
    }


def update_finances(
    agent,
    profit: float,
    cost: float,
    revenue: float,
    is_trip: bool = True,
) -> None:
    agent.capital += profit
    agent.total_profit += profit
    agent.total_cost += cost
    agent.total_revenue += revenue
    agent.wealth = agent.capital

    if is_trip:
        if profit > 0:
            agent.profitable_trip += 1
        else:
            agent.unprofitable_trip += 1

    check_bankruptcy(agent)


def check_bankruptcy(agent) -> None:
    bankruptcy_threshold = -(agent.cost_existence * 7)

    if agent.capital < bankruptcy_threshold:
        agent.bankrupt = True


def get_financial_summary(agent) -> Dict[str, Any]:
    total_trips = agent.profitable_trip + agent.unprofitable_trip

    return {
        "capital": agent.capital,
        "wealth": agent.wealth,
        "total_revenue": agent.total_revenue,
        "total_costs": agent.total_cost,
        "total_profit": agent.total_profit,
        "total_catch": agent.total_catch,
        "profitable_trips": agent.profitable_trip,
        "unprofitable_trips": agent.unprofitable_trip,
        "total_trips": total_trips,
        "success_rate": (
            agent.profitable_trip / total_trips if total_trips > 0 else 0
        ),
        "avg_profit_per_trip": (
            agent.total_profit / total_trips if total_trips > 0 else 0
        ),
        "bankrupt": agent.bankrupt,
    }