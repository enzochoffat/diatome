from typing import Optional, Tuple
from src import config
from src.domain.environment import distance


def is_restricted(self, x: int, y: int) -> bool:
        if self.restricted_mask is None:
            return False
        return self.restricted_mask[y][x]


def move_to(self, x: int, y: int) -> None:
        if not (
            0 <= x < self.model.grid.width
            and 0 <= y < self.model.grid.height
        ):
            return

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
        if from_pos is None or to_pos is None:
            return 0.0
        price = distance.get_distance(to_pos[0], to_pos[1])
        return price
