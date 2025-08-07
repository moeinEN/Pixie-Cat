import math
from behaviors.base import Behavior
from pointer import get_mouse_position

class Attack(Behavior):
    asset         = "assets/attack.gif"
    step          = 0
    move_interval = 100
    fps           = 12
    duration_ms   = 1000

    def __init__(self, width, height):
        super().__init__(width, height)
        self.previous_facing = 1

    def start(self):
        pass

    def stop(self):
        pass

    def update(self, x: float, y: float):
        pos = get_mouse_position()
        if pos:
            px, py = pos

            left_thresh  = 15
            right_thresh = 35


            if px <= left_thresh:
                facing =  -1
            elif px >= right_thresh:
                facing = 1
            else:
                facing = self.previous_facing
        else:
            facing = getattr(self, "previous_facing", 1)

        self.previous_facing = facing
        return x, y, facing