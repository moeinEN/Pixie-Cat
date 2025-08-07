import abc

class Behavior(abc.ABC):
    asset: str
    step: int
    move_interval: int
    fps: int

    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height

    def start(self):
        """Called when this behavior becomes active."""
        pass

    def stop(self):
        """Called when this behavior is deactivated."""
        pass

    @abc.abstractmethod
    def update(self, x: float, y: float) -> tuple[float, float, int]:
        """
        Called each move tick.
        Return (new_x, new_y, facing), where facing is +1 or -1.
        """
        ...