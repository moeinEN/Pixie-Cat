from .base import Behavior

class Sit(Behavior):
    asset         = "assets/sit.gif"
    step          = 0
    move_interval = 1000
    fps           = 1

    def start(self):
        pass

    def stop(self):
        pass

    def update(self, x, y):
        return x, y, 1