import random, math

class WalkBehavior:
    def __init__(self, width: int, height: int, step: int):
        self.w = width
        self.h = height
        self.step = step
        self.steps = 0
        self._pick_target()

    def _pick_target(self):
        self.tx = random.uniform(0, self.w)
        self.ty = random.uniform(0, self.h)

    def next(self, x: float, y: float):
        dx = self.tx - x
        dy = self.ty - y
        dist = math.hypot(dx, dy)
        # if close to target or random turn chance, pick new target
        if dist < self.step or random.random() < 0.01:
            self._pick_target()
            dx = self.tx - x
            dy = self.ty - y
            dist = math.hypot(dx, dy)
        # no movement
        if dist == 0:
            return x, y, 1
        # compute next position
        nx = x + (dx / dist) * self.step
        ny = y + (dy / dist) * self.step
        # clamp to bounds
        nx = max(0, min(nx, self.w))
        ny = max(0, min(ny, self.h))
        self.steps += self.step
        facing = 1 if dx >= 0 else -1
        # if hit edge, choose new target
        if nx == 0 or nx == self.w or ny == 0 or ny == self.h:
            self._pick_target()
        return nx, ny, facing
