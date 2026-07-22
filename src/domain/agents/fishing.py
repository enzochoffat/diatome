from typing import Dict, Any, Tuple

import numpy as np

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

    # --- Catch calculation (per species) ---
    if agent.fisher_type == "coastal":
        catch_vec, total_catch, total_revenue = _coastal_catch(agent, location, patch, current_region)
    else:
        catch_vec, total_catch, total_revenue = _simple_catch(agent, location)

    actual_catch = total_catch

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
        agent.accumulated_value += total_revenue
        agent.days_at_sea += 1

    else:
        result = finance.calculate_profit(agent, total_revenue, total_cost)

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

    agent.update_memory_good_spots(location, total_revenue, agent.expected_revenue)

    if agent.fisher_type == "trawler":
        profit_out = -total_cost
        revenue_out = 0.0
    else:
        profit_out = total_revenue - total_cost
        revenue_out = total_revenue

    return {
        "catch": actual_catch,
        "costs": total_cost,
        "profit": profit_out,
        "revenue": revenue_out,
        "location": location,
    }


def _simple_catch(agent, location) -> Tuple[np.ndarray, float, float]:
    """Per-species catch for non-coastal agents.

    Returns:
        (catch_vector, total_catch_tonnes, total_revenue)
    """
    f_idx = agent.model.flotilla_indices[agent.fisher_type]
    catchability_vec = agent.catchability_vector
    price_vec = agent.model.price_matrix[f_idx]
    biomass_vec = agent.model.species_biomass[location[0], location[1], :]

    available = np.maximum(biomass_vec, 0.0)
    catch_vec = np.minimum(catchability_vec, available)
    agent.model.species_biomass[location[0], location[1], :] -= catch_vec
    agent.model._sync_patch_fish_stock(location[0], location[1])

    total_catch = float(np.sum(catch_vec))
    total_revenue = float(np.sum(catch_vec * price_vec))
    return catch_vec, total_catch, total_revenue


def _coastal_catch(agent, location, patch, current_region) -> Tuple[np.ndarray, float, float]:
    """Per-species catch split over two cells for coastal agents.

    Returns:
        (catch_vector, total_catch_tonnes, total_revenue)
    """
    f_idx = agent.model.flotilla_indices[agent.fisher_type]
    catchability_vec = agent.catchability_vector
    price_vec = agent.model.price_matrix[f_idx]

    neighbors = agent.get_neighbor_positions_in_radius(location, radius=1)

    same_region_neighbors = [
        (nx, ny)
        for nx, ny in neighbors
        if (n_patch := agent.model.get_patch_info(nx, ny))
        and n_patch["region"] == current_region
    ]

    if same_region_neighbors:
        other_pos = same_region_neighbors[0]
        catch_here_vec = catchability_vec * 0.5
        catch_other_vec = catchability_vec - catch_here_vec

        biomass_here = agent.model.species_biomass[location[0], location[1], :]
        biomass_other = agent.model.species_biomass[other_pos[0], other_pos[1], :]

        available_here = np.maximum(biomass_here, 0.0)
        available_other = np.maximum(biomass_other, 0.0)

        actual_here = np.minimum(catch_here_vec, available_here)
        agent.model.species_biomass[location[0], location[1], :] -= actual_here

        actual_other = np.minimum(catch_other_vec, available_other)
        agent.model.species_biomass[other_pos[0], other_pos[1], :] -= actual_other

        agent.model._sync_patch_fish_stock(location[0], location[1])
        agent.model._sync_patch_fish_stock(other_pos[0], other_pos[1])

        catch_vec = actual_here + actual_other
    else:
        biomass_here = agent.model.species_biomass[location[0], location[1], :]
        available_here = np.maximum(biomass_here, 0.0)
        catch_vec = np.minimum(catchability_vec, available_here)
        agent.model.species_biomass[location[0], location[1], :] -= catch_vec
        agent.model._sync_patch_fish_stock(location[0], location[1])

    total_catch = float(np.sum(catch_vec))
    total_revenue = float(np.sum(catch_vec * price_vec))
    return catch_vec, total_catch, total_revenue


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

    # Revenue is already tracked per-day during fishing.
    # At landing, just add the accumulated value.
    revenue = agent.accumulated_value
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
    agent.accumulated_value = 0.0
    agent.days_in_current_trip = 0
    agent.jumped = False
    agent.gone_fishing = False
    agent.at_sea = False