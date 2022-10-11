from threading import Event, Thread


class Threaded(Thread):
    def __init__(self):
        super().__init__()

        self.terminate_flag = Event()

    def stop(self):
        self.terminate_flag.set()
