import numpy as np

from pathlib import Path

from src import config
from src.core.agent import FisherAgent
from src.infrastructure.loader import ConfigLoader
from src.infrastructure.ports.ports_loader import (
    get_port_coordinates,
)
from src.domain.environment.distance import create_distance_map, save_distance_map

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _get_effort_func(self):
    """Returns a callable (port_idx, flotilla_col) -> effort_quota."""
    effort_quotas = self.config_loader.apply_effort_quotas() if getattr(self, "config_loader", None) else None
    _flotilla_key = ["archipelagos", "coastal", "trawler"]
    if isinstance(effort_quotas, np.ndarray):
        def _effort(port, col):
            return int(effort_quotas[port, col]) if port < effort_quotas.shape[0] else 0
        return _effort
    elif isinstance(effort_quotas, dict):
        def _effort(port, col):
            return effort_quotas.get(_flotilla_key[col], 0)
        return _effort
    else:
        def _effort(port, col):
            return 0
        return _effort


def create_single_agent(
    self,
    fisher_type: str,
    agent_id: int,
    port_index: int | None = None,
    name: str | None = None,
) -> "FisherAgent":
    """Creates a single fisher agent for dynamic fleet resize.

    Args:
        fisher_type: One of ``archipelago``, ``coastal``, ``trawler``.
        agent_id: Monotone unique_id (never reused).
        port_index: Optional port index. If None, chosen randomly among
            available ports (fallback 0 if no ports map).
        name: Optional display name.

    Returns:
        The created ``FisherAgent`` already registered and placed on grid.
    """
    from src.infrastructure.ports.ports_loader import get_port_coordinates

    port_coordinates = get_port_coordinates()
    if not port_coordinates:
        # Fallback: at least one dummy port at (0,0)
        port_coordinates = [(0, 0)]

    if port_index is None:
        # Requirement 3: port associé aléatoirement
        port_index = self.random.choice(list(range(len(port_coordinates))))

    # Clamp port_index to valid range
    port_index = int(port_index) % len(port_coordinates)
    port_coord = port_coordinates[port_index]

    # Habitat is fleet-specific, same for all agents of a flotilla
    habitat_dict = (
        self.config_loader.get_habitat_assignments()
        if getattr(self, "config_loader", None)
        else {}
    )
    landings_quotas = (
        self.config_loader.apply_landings_quotas()
        if getattr(self, "config_loader", None)
        else {}
    )
    _effort = _get_effort_func(self)

    flotilla_col = {"archipelago": 0, "coastal": 1, "trawler": 2}[fisher_type]
    effort_quota = _effort(port_index, flotilla_col)

    # Habitat key mapping
    habitat_key_map = {
        "archipelago": "archipelago_habitats",
        "coastal": "coastal_habitats",
        "trawler": "trawler_habitats",
    }
    landings_key_map = {
        "archipelago": "archipelagos",
        "coastal": "coastal",
        "trawler": "trawler",
    }
    habitat = self.restricted_habitat(
        habitat_dict.get(habitat_key_map[fisher_type], [0])
    )
    landings_quota = landings_quotas.get(landings_key_map[fisher_type], [0])

    distance_map = create_distance_map(self, port_location=port_coord)

    agent = FisherAgent(
        agent_id,
        self,
        fisher_type,
        initial_capital=getattr(self, "initial_capital", None),
        name=name,
        port=port_coord,
        habitat=habitat,
        distance_map=distance_map,
        effort_quotas=effort_quota,
        landing_quotas=landings_quota,
    )

    # Placement
    if fisher_type == "archipelago":
        start_pos = (0, 0)
        self.grid.place_agent(agent, start_pos)
        agent.current_location = start_pos
    else:
        water_cells = config.WATER_CELLS
        if water_cells:
            start_pos = tuple(self.random.choice(water_cells))
            self.grid.place_agent(agent, start_pos)
            agent.current_location = start_pos
        else:
            # Fallback if no water cells loaded yet
            start_pos = (0, 0)
            self.grid.place_agent(agent, start_pos)
            agent.current_location = start_pos

    # Keep Mesa counter in sync (since we override unique_id)
    if hasattr(self, "_next_agent_id"):
        if agent_id >= self._next_agent_id:
            self._next_agent_id = agent_id + 1
    if hasattr(self, "agent_id_counter"):
        if agent_id >= self.agent_id_counter:
            self.agent_id_counter = agent_id + 1

    return agent


def create_agents(self) -> None:
    agent_id = 0
    effort_quotas = self.config_loader.apply_effort_quotas() if getattr(self, "config_loader", None) else None
    landings_quotas = self.config_loader.apply_landings_quotas() if getattr(self, "config_loader", None) else {}
    ports_dict = (
        self.config_loader.get_port_assignments()
        if self.config_loader
        else {}
    )

    habitat_dict = (
        self.config_loader.get_habitat_assignments()
        if self.config_loader
        else {}
    )

    port_coordinates = get_port_coordinates()

    _flotilla_key = ["archipelagos", "coastal", "trawler"]

    if isinstance(effort_quotas, np.ndarray):
        def _effort(port, col):
            return int(effort_quotas[port, col]) if port < effort_quotas.shape[0] else 0
    elif isinstance(effort_quotas, dict):
        def _effort(port, col):
            return effort_quotas.get(_flotilla_key[col], 0)
    else:
        def _effort(port, col):
            return 0

    for i in range(self.num_archipelago):
        name = (
            self.archipelago_names[agent_id]
            if self.archipelago_names
            else None
        )

        ports = ports_dict.get("archipelago_ports", [0])
        port_index = ports[i]
        effort_quota = _effort(port_index, 0)
        landings_quota = landings_quotas.get("archipelagos", [0])
        habitat = self.restricted_habitat(
            habitat_dict.get(
                "archipelago_habitats",
                [0],
            )
        )

        distance_map = create_distance_map(
            self,
            port_location=port_coordinates[port_index],
        )
        if i == 0:
            save_distance_map(
                distance_map,
                file_path=(
                    _PROJECT_ROOT / "Ecospace_outputs" / "topology"
                    / "Distance.csv"
                ),
            )

        agent = FisherAgent(
            agent_id,
            self,
            "archipelago",
            initial_capital=self.initial_capital,
            name=name,
            port=port_coordinates[port_index],
            habitat=habitat,
            distance_map=distance_map,
            effort_quotas=effort_quota,
            landing_quotas=landings_quota
        )

        start_pos = (0, 0)

        self.grid.place_agent(agent, start_pos)
        agent.current_location = start_pos

        agent_id += 1

    for i in range(self.num_coastal):
        offset = agent_id - self.num_archipelago

        name = (
            self.coastal_names[offset]
            if self.coastal_names
            else None
        )

        ports = ports_dict.get("coastal_ports", [0])
        port_index = ports[i]
        effort_quota = _effort(port_index, 1)
        landings_quota = landings_quotas.get("coastal", [0])
        habitat = self.restricted_habitat(
            habitat_dict.get(
                "coastal_habitats",
                [0],
            )
        )

        agent = FisherAgent(
            agent_id,
            self,
            "coastal",
            initial_capital=self.initial_capital,
            name=name,
            port=port_coordinates[port_index],
            habitat=habitat,
            distance_map=create_distance_map(
                self,
                port_location=port_coordinates[port_index],
            ),
            effort_quotas=effort_quota,
            landing_quotas=landings_quota
        )

        water_cells = config.WATER_CELLS
        start_pos = tuple(self.random.choice(water_cells)) if water_cells else None

        if start_pos is not None:
            self.grid.place_agent(agent, start_pos)
            agent.current_location = start_pos

        agent_id += 1

    for i in range(self.num_trawler):
        offset = (
            agent_id
            - self.num_archipelago
            - self.num_coastal
        )

        name = (
            self.trawler_names[offset]
            if self.trawler_names
            else None
        )

        ports = ports_dict.get("trawler_ports", [0])
        port_index = ports[i]
        effort_quota = _effort(port_index, 2)
        landings_quota = landings_quotas.get("trawler", [0])

        habitat = self.restricted_habitat(
            habitat_dict.get(
                "trawler_habitats",
                [0],
            )
        )

        agent = FisherAgent(
            agent_id,
            self,
            "trawler",
            initial_capital=self.initial_capital,
            name=name,
            port=port_coordinates[port_index],
            habitat=habitat,
            distance_map=create_distance_map(
                self,
                port_location=port_coordinates[port_index],
            ),
            effort_quotas=effort_quota,
            landing_quotas=landings_quota            
        )

        water_cells = config.WATER_CELLS
        start_pos = tuple(self.random.choice(water_cells)) if water_cells else None

        if start_pos is not None:
            self.grid.place_agent(agent, start_pos)
            agent.current_location = start_pos

        agent_id += 1
