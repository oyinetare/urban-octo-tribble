import threading
import time


class SnowflakeID:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, datacenter_id: int, worker_id: int):
        del (
            datacenter_id,
            worker_id,
        )  # Required by __init__, but unused in __new__ (This is intentional for the singleton pattern)
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, datacenter_id: int, worker_id: int):
        if not hasattr(self, "initialized"):
            self.datacenter_id = datacenter_id
            self.worker_id = worker_id
            self.sequence = 0
            self.last_timestamp = -1
            self.lock = threading.Lock()

            # Epoch (custom start time)
            self.epoch = 1288834974657  # Twitter's epoch

            # Bit lengths
            self.datacenter_bits = 5
            self.worker_bits = 5
            self.sequence_bits = 12

            # Max values
            self.max_datacenter = (1 << self.datacenter_bits) - 1
            self.max_worker = (1 << self.worker_bits) - 1
            self.max_sequence = (1 << self.sequence_bits) - 1

            self.initialized = True

    def _current_timestamp(self) -> int:
        return int(time.time() * 1000)

    def generate(self) -> int:
        with self.lock:
            timestamp = self._current_timestamp()

            # Clock moved backwards - wait
            if timestamp < self.last_timestamp:
                raise Exception(f"Clock moved backwards by {self.last_timestamp - timestamp}ms")

            if timestamp == self.last_timestamp:
                # Same millisecond - increment sequence
                self.sequence = (self.sequence + 1) & self.max_sequence
                if self.sequence == 0:
                    # Sequence overflow - wait for next millisecond
                    timestamp = self._wait_next_millis(self.last_timestamp)
            else:
                # New millisecond - reset sequence
                self.sequence = 0

            self.last_timestamp = timestamp

            # Build ID
            return (
                ((timestamp - self.epoch) << 22)
                | (self.datacenter_id << 17)
                | (self.worker_id << 12)
                | self.sequence
            )

    def _wait_next_millis(self, last_timestamp: int) -> int:
        timestamp = self._current_timestamp()
        while timestamp <= last_timestamp:
            timestamp = self._current_timestamp()
        return timestamp


# Initialize once
id_generator = SnowflakeID(datacenter_id=1, worker_id=1)
