from typing import Dict, Any, Tuple

from src.domain.agents import finance


def go_fish(agent, location: Tuple[int, int]) -> Dict[str, Any]:
    patch = agent.model.get_patch_info(location[0], location[1])

    if not patch:
        return {
            "catch": 0,
            "costs": 0,
            "profit": 0,
            "revenue": 0,
            "location": location,
        }

    current_region = patch["region"]

    # --- Catch calculation ---
    if agent.fisher_type == "coastal":
        actual_catch = _coastal_catch(agent, location, patch, current_region)
    else:
        available_stock = patch["fish_stock"]
        potential_catch = min(agent.catchability, available_stock)

        actual_catch = agent.model.reduce_stock(
            location[0], location[1], potential_catch
        )

    # --- Travel cost ---
    if agent.fisher_type in ("archipelago", "coastal"):
        travel_cost = agent.get_travel_cost(current_region)
    elif agent.fisher_type == "trawler":
        travel_cost = _trawler_travel_cost(
            agent, location, actual_catch, current_region
        )
    else:
        travel_cost = 0.0

    total_cost = agent.cost_existence + agent.cost_activity + travel_cost

    # --- Financial update ---
    if agent.fisher_type == "trawler":
        finance.update_finances(
            agent,
            profit=-total_cost,
            cost=total_cost,
            revenue=0.0,
            is_trip=False,
        )

        agent.accumulated_catch += actual_catch
        agent.fish_onboard += actual_catch
        agent.days_at_sea += 1

    else:
        result = finance.calculate_profit(agent, actual_catch, total_cost)

        if result["profit"] > 0:
            agent.profitable_trip += 1
        else:
            agent.unprofitable_trip += 1

        finance.update_finances(
            agent,
            result["profit"], result["costs"], result["revenue"],
            is_trip=True,
        )

        agent.accumulated_catch += actual_catch
        agent.days_at_sea += 1
        agent.total_catch += actual_catch

    agent.update_memory_good_spots(location, actual_catch, agent.catchability)

    if agent.fisher_type == "trawler":
        profit_out = -total_cost
        revenue_out = 0.0
    else:
        profit_out = actual_catch * agent.model.FISH_PRICE - total_cost
        revenue_out = actual_catch * agent.model.FISH_PRICE

    return {
        "catch": actual_catch,
        "costs": total_cost,
        "profit": profit_out,
        "revenue": revenue_out,
        "location": location,
    }


def _coastal_catch(agent, location, patch, current_region) -> float:
    stock_here = patch["fish_stock"]

    neighbors = agent.get_neighbor_positions_in_radius(location, radius=1)

    same_region_neighbors = [
        ((nx, ny), agent.model.get_patch_info(nx, ny))
        for nx, ny in neighbors
        if (n_patch := agent.model.get_patch_info(nx, ny))
        and n_patch["region"] == current_region
    ]

    if same_region_neighbors:
        other_pos, other_patch = same_region_neighbors[0]

        stock_other = other_patch["fish_stock"]

        catch_here = round(0.5 * agent.catchability)
        catch_other = agent.catchability - catch_here

        actual_here = agent.model.reduce_stock(
            location[0], location[1], catch_here
        )

        actual_other = agent.model.reduce_stock(
            other_pos[0], other_pos[1], catch_other
        )

        return actual_here + actual_other

    return agent.model.reduce_stock(
        location[0], location[1], min(agent.catchability, stock_here)
    )


def _trawler_travel_cost(agent, location, actual_catch, current_region) -> float:
    if not agent.gone_fishing:
        travel_cost = agent.get_travel_cost(current_region)
    else:
        if agent.jumped:
            travel_cost = agent.get_travel_cost(current_region) / 2
            agent.jumped = False
        else:
            travel_cost = 0.0

    if agent.fish_onboard + actual_catch >= agent.storing_capacity:
        agent.gone_fishing = False
    else:
        agent.gone_fishing = True

    return travel_cost


def land_fish(agent) -> None:
    if agent.fisher_type != "trawler" or agent.fish_onboard <= 0:
        return

    revenue = agent.fish_onboard * agent.model.FISH_PRICE

    agent.capital += revenue
    agent.wealth += revenue
    agent.total_revenue += revenue
    agent.total_catch += agent.fish_onboard

    if revenue > 0:
        agent.profitable_trip += 1
    else:
        agent.unprofitable_trip += 1

    agent.fish_onboard = 0.0
    agent.accumulated_catch = 0.0
    agent.days_in_current_trip = 0
    agent.jumped = False
    agent.gone_fishing = False
    agent.at_sea = False