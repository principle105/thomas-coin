import time
from threading import Thread
from constants import BLOCK_INTERVAL


class Validator(Thread):
    def __init__(self, chain):
        super().__init__(daemon=True)
        self.chain = chain

        self._stop = False

    def run(self):
        while not self.__stop:
            self.check_block()
            if int(time.time()) % BLOCK_INTERVAL == 0:
                self.create_new_block(self)

    def create_new_block(self):
        pass

    def check_block(self):
        pass

    def stop(self):
        self.__stop = True
