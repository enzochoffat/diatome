from typing import Optional, Tuple
from src import config
from src.domain.environment import distance

def is_restricted(self, x: int, y: int) -> bool:
        """Checks whether a location is restricted by habitat or topology.

        Args:
            x: X-coordinate of the location.
            y: Y-coordinate of the location.
        
        Returns:
            True if the location is restricted, False otherwise.
        """
        if self.restricted_mask is None:
            return False
        return self.restricted_mask[y][x]

def move_to(self, x: int, y: int) -> None:
        """Moves the agent to ``(x, y)`` on the Mesa grid.

        Args:
            x: Target column.
            y: Target row.
        """
        if is_restricted(self, x, y):
            return 
        
        if self.pos is not None:
            self.model.grid.remove_agent(self)
        self.model.grid.place_agent(self, (x, y))
        self.current_location = (x, y)
        self.display_location = (x, y)

def calculate_travel_cost(
        self,
        from_pos: Optional[Tuple[int, int]],
        to_pos: Optional[Tuple[int, int]],
    ) -> float:
        """Calculates Euclidean distance-based travel cost.

        Args:
            from_pos: Starting ``(x, y)`` position.
            to_pos: Destination ``(x, y)`` position.

        Returns:
            Travel cost in SEK, or 0 if either position is None.
        """
        if from_pos is None or to_pos is None:
            return 0.0
        price = distance.get_distance(to_pos[0], to_pos[1])
        return price

def get_travel_cost(self, region: str) -> float:
        """Returns the fixed travel cost to a named region.

        Args:
            region: Destination region identifier.

        Returns:
            Travel cost in SEK. Returns 0 for unrecognised regions.
        """
        if region == "A":
            return self.model.LOW_COST_TRAVEL
        if region == "B":
            return (
                self.model.MEDIUM_COST_TRAVEL_BIGVESSEL
                if self.fisher_type == "trawler"
                else self.model.MEDIUM_COST_TRAVEL
            )
        if region in {"C", "D"}:
            return self.model.HIGH_COST_TRAVEL
        return 0.0

