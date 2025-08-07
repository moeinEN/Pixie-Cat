import random, math
from behaviors.base import Behavior

class Run(Behavior):
    asset         = "assets/run.gif"
    step          = 8
    move_interval = 16
    fps           = 24

    def __init__(self, width, height):
        super().__init__(width, height)
        self.steps = 0
        self._pick_target()

    def _pick_target(self):
        self.tx = random.uniform(0, self.w)
        self.ty = random.uniform(0, self.h)

    def start(self):
        self.steps = 0
        self._pick_target()

    def stop(self):
        pass

    def update(self, x, y):
        dx, dy = self.tx - x, self.ty - y
        dist   = math.hypot(dx, dy)
        if dist < self.step or random.random() < 0.05:
            self._pick_target()
            dx, dy = self.tx - x, self.ty - y
            dist   = math.hypot(dx, dy)

        if dist == 0:
            return x, y, 1

        nx = x + dx/dist * self.step
        ny = y + dy/dist * self.step
        nx = max(0, min(nx, self.w))
        ny = max(0, min(ny, self.h))
        self.steps += self.step

        if nx in (0, self.w) or ny in (0, self.h):
            self._pick_target()

        facing = 1 if dx >= 0 else -1
        return nx, ny, facing