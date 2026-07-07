from typing import Any, Dict, List, Optional, Tuple
import statistics


def update_memory(agent, trip_info: Dict[str, Any]) -> None:
    agent.memory.append(trip_info)

    if len(agent.memory) > agent.memory_size:
        agent.memory.pop(0)


def update_memory_good_spots(
    agent,
    location: Tuple[int, int],
    catch: float,
    expected_catch: float,
) -> None:
    catch_efficiency = catch / expected_catch if expected_catch > 0 else 0.0

    if location in agent.good_spots_memory:
        spot = agent.good_spots_memory[location]
        total_visits = spot["visits"]

        spot["avg_catch"] = (
            spot["avg_catch"] * total_visits + catch
        ) / (total_visits + 1)

        spot["visits"] += 1
        spot["last_visit"] = agent.model.current_step
        spot["efficiency"] = catch_efficiency
    else:
        agent.good_spots_memory[location] = {
            "avg_catch": catch,
            "visits": 1,
            "last_visit": agent.model.current_step,
            "efficiency": catch_efficiency,
        }

    agent.good_spots_memory[location]["is_good"] = (
        catch_efficiency >= agent.good_spots_threshold
    )


def get_good_spots(
    agent,
    region: Optional[str] = None,
    min_visits: int = 1,
) -> List[Tuple[Tuple[int, int], Dict[str, Any]]]:
    good_spots = []

    for location, memory in agent.good_spots_memory.items():
        if memory["visits"] < min_visits:
            continue

        if not memory.get("is_good", False):
            continue

        if region is not None:
            patch = agent.model.get_patch_info(location[0], location[1])

            if patch and patch["region"] != region:
                continue

        good_spots.append((location, memory))

    good_spots.sort(key=lambda item: item[1]["avg_catch"], reverse=True)

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