from .base import Behavior
from ..pointer import get_mouse_position

class Happy(Behavior):
    asset         = "assets/happy.gif"
    step          = 0
    move_interval = 100
    fps           = 12
    duration_ms   = 1000

    def __init__(self, width, height, scale=1.0):
        super().__init__(width, height)
        self.scale = scale
        self.previous_facing = 1

    def start(self): pass
    def stop(self):  pass

    def update(self, x: float, y: float):
        pos = get_mouse_position()
        if pos:
            px, _ = pos
            left_thresh  = (25 * self.scale)
            right_thresh = (25 * self.scale)

            if px <= left_thresh:
                facing = -1
            elif px > right_thresh:
                facing =  1
        else:
            facing = self.previous_facing

        return x, y, facing