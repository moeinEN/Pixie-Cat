from behaviors.base import Behavior

class Idle(Behavior):
    asset         = "assets/idle.gif"
    step          = 0
    move_interval = 1000
    fps           = 1

    def start(self):
        pass

    def stop(self):
        pass

    def update(self, x, y):
        return x, y, 1