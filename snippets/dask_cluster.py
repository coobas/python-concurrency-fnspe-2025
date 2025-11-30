# %%
import time

import dask
from dask.distributed import Client


def main() -> None:
    with dask.config.set({"distributed.worker.resources.GPU": 2}):
        client = Client()
    print(client.dashboard_link)
    print(f"Scheduler: {client.scheduler}")
    print(f"Scheduler address: {client.scheduler.address}")
    try:
        while True:
            time.sleep(1)
            client.forward_logging()
    except KeyboardInterrupt:
        pass
    finally:
        client.close()


if __name__ == "__main__":
    main()
