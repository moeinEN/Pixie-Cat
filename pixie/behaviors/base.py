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
        pass

    def stop(self):
        pass

    @abc.abstractmethod
    def update(self, x: float, y: float) -> tuple[float, float, int]:
        ...