from time import perf_counter


class ExecutionTimer:

    def __init__(self):

        self.start_time = 0.0

    def start(self):

        self.start_time = perf_counter()

    def stop(self):

        return (perf_counter() - self.start_time) * 1000