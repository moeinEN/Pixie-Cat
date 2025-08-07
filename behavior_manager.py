from behaviors.walk import Walk
from behaviors.sit  import Sit
from behaviors.run  import Run
import random, gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib

class BehaviorManager:
    def __init__(self, width, height):
        self._behaviors = {
            "walk": Walk(width, height),
            "sit":  Sit(width, height),
            "run":  Run(width, height),
        }
        self.current = self._behaviors["walk"]
        self.current.start()
        self._sit_timer = None

    def update(self, x, y):
        nx, ny, facing = self.current.update(x, y)

        if isinstance(self.current, Walk) and self.current.steps >= self.current.step_limit:
            self.switch("sit")

        if isinstance(self.current, Run) and self.current.steps >= self.current.step_limit:
            self.switch("walk")

        return nx, ny, facing
    
    def switch(self, mode_name):
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

    def _on_sit_timeout(self):
        self.switch("walk")
        return False

    def mode(self):
        return type(self.current).__name__.lower()

    def get_asset(self):
        return self.current.asset

    def get_step(self):
        return self.current.step

    def get_move_interval(self):
        return self.current.move_interval

    def get_fps(self):
        return self.current.fps

    def get_steps(self):
        return getattr(self.current, "steps", 0)
