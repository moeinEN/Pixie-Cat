import random
import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib

from behaviors.walk   import Walk
from behaviors.sit    import Sit
from behaviors.run    import Run
from behaviors.idle   import Idle
from behaviors.attack import Attack
from behaviors.happy  import Happy

class BehaviorManager:
    def __init__(self, width: int, height: int, scale: float = 1.0):
        self.width  = width
        self.height = height
        self.scale  = float(scale) if scale else 1.0

        self._behaviors = {
            "walk":   Walk(width, height),
            "sit":    Sit(width, height),
            "run":    Run(width, height),
            "idle":   Idle(width, height),
            "attack": Attack(width, height, scale=self.scale),
            "happy":  Happy(width, height, scale=self.scale),
        }
        self.current = self._behaviors["walk"]
        self.current.start()

        self._sit_timer  = None
        self._idle_timer = None

    def update(self, x: float, y: float):
        res = self.current.update(x, y)
        if isinstance(self.current, Attack) and res is None:
            self.switch("walk")
            res = self.current.update(x, y)
        nx, ny, facing = res

        from behaviors.walk import Walk
        if isinstance(self.current, Walk) and self.current.steps >= self.current.step_limit:
            self.switch("sit")

        from behaviors.run import Run
        if isinstance(self.current, Run) and self.current.steps >= self.current.step_limit:
            self.switch("walk")

        from behaviors.sit import Sit
        if isinstance(self.current, Sit) and self._sit_timer is None:
            delay = int(random.uniform(7, 15) * 1000)
            self._sit_timer = GLib.timeout_add(delay, self._on_sit_timeout)

        from behaviors.idle import Idle
        if isinstance(self.current, Idle) is False and isinstance(self.current, Walk) and self._idle_timer is None:
            if random.random() < 0.002:
                self.switch("idle")
                self._idle_timer = GLib.timeout_add(5000, self._on_idle_timeout)

        return nx, ny, facing

    def _on_sit_timeout(self):
        self.switch("walk")
        self._sit_timer = None
        return False

    def _on_idle_timeout(self):
        self.switch("walk")
        self._idle_timer = None
        return False

    def switch(self, mode_name: str):
        if mode_name not in self._behaviors:
            return
        new = self._behaviors[mode_name]
        if new is self.current:
            return

        if self._sit_timer:
            GLib.source_remove(self._sit_timer); self._sit_timer = None
        if self._idle_timer:
            GLib.source_remove(self._idle_timer); self._idle_timer = None
        leaving_walk_for_soft = isinstance(self.current, Walk) and mode_name in ("idle", "attack", "happy")
        if not leaving_walk_for_soft:
            self.current.stop()

        if mode_name == "walk" and isinstance(self.current, (Idle, Attack, Happy)):
            self.current = new
            return

        if mode_name == "attack":
            self.current = new
        else:
            self.current = new
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