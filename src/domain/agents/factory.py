from src.core.agent import FisherAgent
from src import config
from src.infrastructure.ports.ports_loader import get_port_coordinates


def create_agents(self) -> None:
        """Creates and places all fisher agents on the grid.

        Instantiates archipelago, coastal, and trawler agents in order,
        assigning each a starting position within an appropriate region.
        """
        agent_id = 0

        ports_dict = self.config_loader.get_port_assignments() if self.config_loader else {}
        port_coords = get_port_coordinates()

        habitat_dict = self.config_loader.get_habitat_assignments() if self.config_loader else {}


        

        for i in range(self.num_archipelago):
            name = (
                self.archipelago_names[agent_id]
                if self.archipelago_names
                else None
            )
            port = ports_dict.get("archipelago_ports", [0])
            index = port[i]
            habitat = self.restricted_area(habitat_dict.get("archipelago_habitats", [0]))
            agent = FisherAgent(
                agent_id, self, "archipelago",
                initial_capital=self.initial_capital, name=name, port=port_coords[index], habitat=habitat
            )
            start_pos = (0, 0)
            if start_pos:
                self.grid.place_agent(agent, start_pos)
                agent.current_location = start_pos
                agent.current_region = self.get_region(*start_pos)
            agent_id += 1

        for i in range(self.num_coastal):
            offset = agent_id - self.num_archipelago
            name = (
                self.coastal_names[offset] if self.coastal_names else None
            )
            port = ports_dict.get("coastal_ports", [0])
            index = port[i]
            habitat = self.restricted_area(habitat_dict.get("coastal_habitats", [0]))
            agent = FisherAgent(
                agent_id, self, "coastal",
                initial_capital=self.initial_capital, name=name, port=port_coords[index], habitat=habitat
            )
            region = self.random.choice(["A", "B"])
            start_pos = self._get_random_position_in_region(region)
            if start_pos:
                self.grid.place_agent(agent, start_pos)
                agent.current_location = start_pos
                agent.current_region = region
            agent_id += 1

        for i in range(self.num_trawler):
            offset = agent_id - self.num_archipelago - self.num_coastal
            name = (
                self.trawler_names[offset] if self.trawler_names else None
            )
            port = ports_dict.get("trawler_ports", [0])
            index = port[i]
            habitat = self.restricted_area(habitat_dict.get("trawler_habitats", [0]))
            agent = FisherAgent(
                agent_id, self, "trawler",
                initial_capital=self.initial_capital, name=name, port=port_coords[index], habitat=habitat
            )
            region = self.random.choice(config.TRAWLER_ACCESSIBLE_REGIONS)
            start_pos = self._get_random_position_in_region(region)
            if start_pos:
                self.grid.place_agent(agent, start_pos)
                agent.current_location = start_pos
                agent.current_region = region
            agent_id += 1
