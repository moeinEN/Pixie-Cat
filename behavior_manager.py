import random
import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib

from behaviors.walk import Walk
from behaviors.run  import Run
from behaviors.sit  import Sit

class BehaviorManager:
    def __init__(self, width: int, height: int):
        self._behaviors = {
            "walk": Walk(width, height),
            "sit":  Sit(width, height),
            "run":  Run(width, height),
        }
        self.current    = self._behaviors["walk"]
        self.current.start()
        self._sit_timer = None

    def update(self, x: float, y: float):
        nx, ny, facing = self.current.update(x, y)

        if isinstance(self.current, Walk) and self.current.steps >= self.current.step_limit:
            self.switch("sit")

        if isinstance(self.current, Run) and self.current.steps >= self.current.step_limit:
            self.switch("walk")

        if isinstance(self.current, Sit) and self._sit_timer is None:
            delay = int(random.uniform(7, 15) * 1000)
            self._sit_timer = GLib.timeout_add(delay, self._on_sit_timeout)

        return nx, ny, facing

    def _on_sit_timeout(self):
        self.switch("walk")
        self._sit_timer = None
        return False

    def switch(self, mode_name: str):
        if mode_name not in self._behaviors:
            return
        if self.current is self._behaviors[mode_name]:
            return

        if self._sit_timer:
            GLib.source_remove(self._sit_timer)
            self._sit_timer = None

        self.current.stop()
        self.current = self._behaviors[mode_name]
        self.current.start()

    def mode(self) -> str:
        return type(self.current).__name__.lower()

    def get_asset(self) -> str:
        return self.current.asset

    def get_step(self) -> int:
        return self.current.step

    def get_move_interval(self) -> int:
        return self.current.move_interval

    def get_fps(self) -> int:
        return self.current.fps

    def get_steps(self) -> int:
        return getattr(self.current, "steps", 0)