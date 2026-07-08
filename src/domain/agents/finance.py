from typing import Any


def calculate_profit(
    agent,
    catch: float,
    costs: float,
) -> dict[str, Any]:
    """Calculate revenue and profit for a fishing trip.

    Args:
        agent: Fisher agent instance.
        catch: Quantity of fish caught.
        costs: Total trip costs.

    Returns:
        Dictionary containing revenue, costs, profit, catch amount,
        fish price, and location information.
    """
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
    """Update the financial state of an agent.

    Args:
        agent: Fisher agent instance.
        profit: Profit to apply.
        cost: Cost to apply.
        revenue: Revenue to apply.
        is_trip: Whether the financial update corresponds to a fishing
            trip.
    """
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
    """Update the bankruptcy status of an agent.

    Args:
        agent: Fisher agent instance.
    """
    bankruptcy_threshold = -(agent.cost_existence * 7)

    if agent.capital < bankruptcy_threshold:
        agent.bankrupt = True


def get_financial_summary(
    agent,
) -> dict[str, Any]:
    """Return a summary of the agent's financial state.

    Args:
        agent: Fisher agent instance.

    Returns:
        Dictionary containing financial metrics and performance
        indicators.
    """
    total_trips = (
        agent.profitable_trip
        + agent.unprofitable_trip
    )

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
            agent.profitable_trip / total_trips
            if total_trips > 0
            else 0.0
        ),
        "avg_profit_per_trip": (
            agent.total_profit / total_trips
            if total_trips > 0
            else 0.0
        ),
        "bankrupt": agent.bankrupt,
    }