from typing import Any, Dict, List, Optional, Tuple
import statistics


def update_memory(agent, trip_info: Dict[str, Any]) -> None:
    agent.memory.append(trip_info)

    if len(agent.memory) > agent.memory_size:
        agent.memory.pop(0)


def update_memory_good_spots(
    agent,
    location: Tuple[int, int],
    revenue: float,
    expected_revenue: float,
) -> None:
    value_efficiency = revenue / expected_revenue if expected_revenue > 0 else 0.0

    if location in agent.good_spots_memory:
        spot = agent.good_spots_memory[location]
        total_visits = spot["visits"]

        spot["avg_value"] = (
            spot["avg_value"] * total_visits + revenue
        ) / (total_visits + 1)

        spot["visits"] += 1
        spot["last_visit"] = agent.model.current_step
        spot["efficiency"] = value_efficiency
    else:
        agent.good_spots_memory[location] = {
            "avg_value": revenue,
            "visits": 1,
            "last_visit": agent.model.current_step,
            "efficiency": value_efficiency,
        }

    agent.good_spots_memory[location]["is_good"] = (
        value_efficiency >= agent.good_spots_threshold
    )


def get_good_spots(
    agent,
    min_visits: int = 1,
) -> List[Tuple[Tuple[int, int], Dict[str, Any]]]:
    good_spots = []

    for location, spot_memory in agent.good_spots_memory.items():
        if spot_memory["visits"] < min_visits:
            continue

        if not spot_memory.get("is_good", False):
            continue

        good_spots.append((location, spot_memory))

    good_spots.sort(key=lambda item: item[1]["avg_value"], reverse=True)

    return good_spots


def get_memory_statistics(agent) -> Dict[str, Any]:
    if not agent.memory:
        return {
            "avg_profit": 0,
            "avg_catch": 0,
            "avg_cost": 0,
            "success_rate": 0,
            "recent_trend": 0,
        }

    catches = [t["catch"] for t in agent.memory]
    profits = [t["profit"] for t in agent.memory]
    costs = [t["cost"] for t in agent.memory]

    fishing_trips = [
        t for t in agent.memory if t.get("went_fishing", True)
    ]

    if fishing_trips:
        profitable = sum(1 for t in fishing_trips if t["profit"] > 0)
        success_rate = profitable / len(fishing_trips)
    else:
        success_rate = 0.0

    trend = 0.0

    if len(profits) >= 14:
        recent_avg = statistics.mean(profits[-7:])
        older_avg = statistics.mean(profits[-14:-7])

        if older_avg != 0:
            trend = (recent_avg - older_avg) / abs(older_avg)

    return {
        "avg_catch": statistics.mean(catches),
        "median_catch": statistics.median(catches),
        "avg_profit": statistics.mean(profits),
        "median_profit": statistics.median(profits),
        "avg_cost": statistics.mean(costs),
        "success_rate": success_rate,
        "recent_trend": trend,
        "total_trips": len(agent.memory),
    }

def forget_old_spots(agent, max_age_ticks: int) -> None:
    current_tick = agent.model.current_step

    to_remove = [
        loc
        for loc, mem in agent.good_spots_memory.items()
        if current_tick - mem["last_visit"] > max_age_ticks
    ]

    for location in to_remove:
        del agent.good_spots_memory[location]