from src import config
from src.core.agent import FisherAgent
from src.infrastructure.ports.ports_loader import (
    get_port_coordinates,
)
from src.domain.environment.distance import create_distance_map, save_distance_map


def create_agents(self) -> None:
    """Create and place all fisher agents on the grid.

    The method creates archipelago, coastal, and trawler agents,
    assigns them a home port and habitat restrictions, and places
    them at an appropriate starting location.

    Archipelago fishers always start at (0, 0), while coastal and
    trawler fishers start at a random position within one of their
    accessible regions.
    """
    agent_id = 0

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

    for i in range(self.num_archipelago):
        name = (
            self.archipelago_names[agent_id]
            if self.archipelago_names
            else None
        )

        ports = ports_dict.get("archipelago_ports", [0])
        port_index = ports[i]

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
                file_path="C:\\Users\\enzo.choffat\\Documents\\Stage\\code\\diatome\\Ecospace_outputs\\topology\\Distance.csv",
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
        )

        start_pos = (0, 0)

        self.grid.place_agent(agent, start_pos)
        agent.current_location = start_pos
        agent.current_region = self.get_region(*start_pos)

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
        )

        region = self.random.choice(["A", "B"])
        start_pos = self._get_random_position_in_region(region)

        if start_pos is not None:
            self.grid.place_agent(agent, start_pos)
            agent.current_location = start_pos
            agent.current_region = region

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
        )

        region = self.random.choice(
            config.TRAWLER_ACCESSIBLE_REGIONS,
        )

        start_pos = self._get_random_position_in_region(region)

        if start_pos is not None:
            self.grid.place_agent(agent, start_pos)
            agent.current_location = start_pos
            agent.current_region = region

        agent_id += 1