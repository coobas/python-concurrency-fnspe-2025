# %%
import logging
import time

import numpy as np
from dask.distributed import Client, worker_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Dask Demo")


address = "tcp://127.0.0.1:55544"

slowness = 0.3
failure_rate = 0.1
retries_factor = 4


def load_data(size: int, latency_s: float = slowness) -> np.ndarray:
    # Pretend we're fetching from remote storage
    time.sleep(latency_s * 5)
    return np.arange(size, dtype=np.int64)


def check_divisibility_single(data: np.ndarray, by: int) -> np.ndarray:
    if np.random.random() < failure_rate:
        logger.warning("Random failure occurred!")
        raise ValueError("Random failure occurred!")
    # Random sleep to simulate work
    time.sleep(by * slowness * np.random.random())
    return (data % by) == 0


def check_divisibility(data: np.ndarray, divisors: np.ndarray) -> np.ndarray:
    with worker_client() as wc:  # Get Dask worker client
        part_futs = [  # Submit tasks to Dask cluster
            wc.submit(
                check_divisibility_single,
                data,
                by,
                resources={"GPU": 1},  # Tag task with GPU resource
                # Retry task if it fails
                retries=int(np.ceil(1 / failure_rate * retries_factor)),
            )
            for by in divisors
        ]
        parts = wc.gather(part_futs)  # Gather results from Dask cluster
    return np.logical_and.reduce(parts)


def is_divisible_by(
    data: np.ndarray, divisors: np.ndarray, num_chunks: int = 4
) -> np.int64:
    """Check if data is divisible by divisors.

    Args:
        data: Data to check divisibility of.
        divisors: Divisors to check divisibility by.
        num_chunks: Number of chunks to split data into.

    Returns:
        Data that is divisible by divisors.
    """
    # Get Dask worker client
    with worker_client() as wc:
        # Split data into chunks
        chunks = np.array_split(data, num_chunks)
        # Submit tasks to Dask cluster (non-blocking)
        part_futs = [wc.submit(check_divisibility, c, divisors) for c in chunks]
        # Gather results from Dask cluster (blocking)
        parts = wc.gather(part_futs)
    return data[np.concatenate(parts, axis=0)]


# %%

# address = None
client = Client(address)
print(f"Connected to Dask at: {client.dashboard_link}")

# %%
size = 10_000
num_chunks = 10
divisors = np.array([3, 5, 7, 11, 13])

# 1) Load data remotely -> Future
data_future = client.submit(load_data, size)
# 2) Pass the future + extra arg into a function that
# splits work via worker_client
result_future = client.submit(
    is_divisible_by, data_future, divisors=divisors, num_chunks=num_chunks
)
# 3) Wait for the result (blocking)
result: np.ndarray = result_future.result()

# %%
# result
# %%
