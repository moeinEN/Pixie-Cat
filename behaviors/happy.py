import math
from behaviors.base import Behavior
from pointer import get_mouse_position

class Happy(Behavior):
    asset         = "assets/happy.gif"
    step          = 0
    move_interval = 100
    fps           = 12
    duration_ms   = 1000   # or whatever you like

    def __init__(self, width, height):
        super().__init__(width, height)
        self.previous_facing = 1

    def start(self):
        pass

    def stop(self):
        pass

    def update(self, x: float, y: float):
        """
        Stay in place, but face toward the mouse if it’s
        beyond your left/right thresholds.
        """
        pos = get_mouse_position()
        if pos:
            px, py = pos

            # tweak these two to adjust your “dead zone” around the cat’s center:
            left_thresh  = 25   # px coordinate ≤ 15 → mouse is “left”
            right_thresh = 25   # px coordinate ≥ 35 → mouse is “right”

            if px <= left_thresh:
                facing = -1
            elif px > right_thresh:
                facing = 1
            else:
                facing = self.previous_facing
        else:
            # if we can’t read the pointer, keep whatever direction we had
            facing = self.previous_facing

        # remember for next frame
        self.previous_facing = facing
        return x, y, facing