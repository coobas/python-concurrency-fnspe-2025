---
theme: apple-basic
layout: cover
mdc: true

title: Python Concurrency and Distributed Computing in Practice
info: |
  Jakub Urban


---

# Python Concurrency and Distributed Computing in Practice
## Jakub Urban *@ Aisle.com*

---
layout: center
---

# Content

1. Introduction to concurrency and parallelism
2. Python's built-in concurrency primitives
3. Scaling out: Distributed computing with Dask and Ray

---
layout: section
---

# 1. Introduction to concurrency and parallelism


---
layout: two-cols-header
---

# Concurrency lets you wait efficiently

::left::

- Concurrency enables you to **do other things while waiting** for results or resources.
  - For example, you can wait for multiple calculations or API responses.
- It's like a superpower of waiting in multiple queues at once.
- You do not need to care how the queue jobs are processed.

::right::

<v-click>

![Communist Czech queues](./communist_queues.png)
([Foto: Archiv Ladislava Růžičky](https://magazin.aktualne.cz/nemame-zeptejte-se-po-novem-roce-nakupy-za-socialismu-v-cesk/r~49f5bc5a5eba11eebe29ac1f6b220ee8/))
- Would be great for (Czech socialist) queues
  - Sometimes people even did not know what they were waiting for.
  - Wait in multiple queues at once would help.

</v-click>

---
layout: two-cols-header
---

# Parallelism lets you *execute* multiple things at once

::left::

- Parallelism is about **executing multiple things simultaneously**.
- Concurrency does not imply parallelism.
  - Although parallelism is typically desired in concurrent systems.
- Examples of parallel calculation:
  - GPU's or vectorized CPU operations (SIMD - single instruction multiple data).
  - Multi-core machines with shared memory (MIMD - multiple instructions multiple data).
  - Distributed systems: clusters, clouds (MIMD).

::right::

<v-click>

![Parallel sewing](./parallel_sewing.png)

</v-click>

---

# (Data) science cares about both concurrency and parallelism

- In data science, engineering, or high-performance computing, we often care about both concurrency and parallelism.
  - We need processes to be responsive → concurrency.
  - We need to execute calculations fast and efficiently, on large datasets → parallelism.

---
layout: section
---

# 2. Python's built-in concurrency primitives

---

# Python implements built-in concurrency primitives

- `concurrent.futures`
  - > ... provides a high-level interface for asynchronously executing callables.
  - Proposed in 2009: [PEP-3148](https://peps.python.org/pep-3148)
  - We will focus on using and building on these primitives.
- Other standard lib [modules for concurrent execution](https://docs.python.org/3/library/concurrency.html) include:
  - `threading` and `multiprocessing`: parallelism, synchronisation primitives.
  - `subprocess`: subprocess management.
  - `asyncio`: cooperative multitasking.

---

# `from concurrent.futures import Executor`
> Executor is an abstract class that provides methods to execute calls asynchronously.
- This is indeed abstract 😅
- What does one need in particular?
  1. Create an executor: Choose type and parameters.
  2. Submit tasks to the executor.
  3. Collect results.
  4. Shutdown the executor.

```mermaid
flowchart LR
    create["Create executor"]
    submit["Submit tasks"]
    collect["Collect results"]
    shutdown["Shutdown executor"]

    create --> submit --> collect --> shutdown
    collect .-> submit
```

---

# 1. Create an executor

Let's create a process pool executor with 4 workers:

```python
from concurrent.futures import ProcessPoolExecutor

MAX_WORKERS = 4

process_executor = ProcessPoolExecutor(max_workers=MAX_WORKERS)
```

We will see other executor types later.

---

# 2. Submit tasks to the executor

Make the executor do some math:

```python
def do_some_math(x: float) -> float:
    return x * x
```

1. Single calculation via `submit`:
```python
result = thread_executor.submit(do_some_math, 5)
```

2. Multiple calculations via `map`:
```python
results = thread_executor.map(do_some_math, range(10))
```

---

# Where is the concurrency? Meet the `Future` 💡

- Both `submit` and `map` return *immediately*, without waiting for the tasks to complete.
- The output of `submit` is a `concurrent.futures.Future` object:

```python
result = thread_executor.submit(do_some_math, 5)
print(result)
```

```
<Future at 0x122921490 state=finished returned int>
```

- `Future` is a placeholder for the result of a computation that may not be completed yet.
- `Future` encapsulates the asynchronous execution.
- Most important `Future` methods are:
  - `result(timeout=None)`: Waits for the computation to complete and returns the result.
  - `done()`: Returns `True` if the call was successfully cancelled or finished running.
  - `cancel()`: Attempts to cancel the computation.

---

# A typical interaction loop

```mermaid {theme: 'neutral', scale: 0.7}
flowchart LR
    A["Submit task with executor.submit()"] --> B["Immediately do other useful work"]
    B --> C{"future.done()?"}
    C -->|Yes| D["Call future.result() and process the answer"]
    C -->|No| E["Keep working on something else"]
    E --> C
```

---

# Collect multiple results: `map`

- The output of `map` is a generator object:

```python
results = thread_executor.map(do_some_math, range(10))
print(results)
```

```
<generator object Executor.map.<locals>.result_iterator at 0x122a1f4d0>
```

- This generator yields results as they become available, *in the order* they were submitted.
- One would typically iterate over the generator:

```python
for result in results:
    ...
```

- or collect all results into a list:

```python
completed_results = list(results)
```

- Caveat: Slow tasks may block the iteration (although do not block the execution in the workers).

---

# Collect multiple results: `as_completed`

- We can `submit` multiple tasks without using executor's `map` method.
  - This will yield multiple `Future` objects.

```python
futures = [executor.submit(do_some_math, x) for x in range(10)]
```

or using built-in `map`:
```python
futures = map(functools.partial(executor.submit, do_some_math), range(10))
```

- `as_completed` then iterates over a collection of futures *as soon as they complete*:

```python
for future in concurrent.futures.as_completed(futures):
    print(future.result())
```

- This way we can *promptly process the results* without waiting for any slow ones.

---

# More flexibility for multiple results: `wait`

- `wait` gives us more flexibility and control over the futures while waiting.
  - We can use waiting timeout.
  - Can wait for first completed, all completed, or first exception.
  - For example, we can use a few first completed results and cancel the rest.

```python
done, not_done = wait(futures, timeout=1, return_when=FIRST_COMPLETED)
```

- `done` and `not_done` are sets of futures.
- A common pattern is to keep calling `wait` until `not_done` becomes empty, processing completed futures as soon as they're ready:

```python
not_done = [executor.submit(do_some_math, x) for x in range(10)]
while not_done:
    done, not_done = wait(not_done, return_when=FIRST_COMPLETED)
    for future in done:
        handle_result(future.result())  # react immediately
```

---

# TL;DR

- `submit` and `map` return immediately, without waiting for the tasks to complete.
- `Future` is a placeholder for the result.
- Waiting for results can be done in multiple ways:
  - `Future.result()` blocks until the result is available.
  - `map` and `as_completed` yield results as they become available.
  - `wait` gives full control over the waiting process.

---

# 4. Shutdown the executor

- Executors should be shutdown to release resources.
  - This may be done automatically when the executor is garbage collected.
  - The type and released resources depend on the executor type.

```python
executor.shutdown(wait=True, cancel_futures=False)
```

- `wait=True` blocks until all futures are completed and resources are freed.
- `cancel_futures=True` cancels pending futures that have not started running.

- Lifetime can also be managed by a `with` block:

```python
with ThreadPoolExecutor(max_workers=4) as executor:
    result = executor.submit(do_some_math, 5)
```

---

# Executor types

Three executor types exist in `concurrent.futures`:

- `ThreadPoolExecutor`: using threads, suffers from Global Interpreter Lock (GIL).
- `ProcessPoolExecutor`: using sub-processes.
- `InterpreterPoolExecutor`: using interpreters.
  - A subclass of `ThreadPoolExecutor`, added in version 3.14.
  - The biggest benefit is true multi-core parallelism. Each interpreter has its own Global Interpreter Lock (GIL).

---

# Gotcha example: A non-obvious random numbers stale state

```python
list(process_executor.map(np.random.randint, 8*[100]))
```
```text
[51, 51, 51, 51, 51, 51, 51, 51]
```

- Surprisingly, random generator state is shared and not mutated.
- 🤯 `randint` is not a (pure) function, it's a `RandomState` instance's method.

---

# `ThreadPoolExecutor` limitation: Global Interpreter Lock (GIL)

- Global Interpreter Lock (GIL) is probably the most (in)famous limitation of CPython.
- GIL prevents multiple threads from executing Python code simultaneously (in parallel).
- However, GIL can be released by:
  - I/O operations (file operations, network requests).
  - C extensions (NumPy, Pandas, TensorFlow).
- ... thus enabling threads to run in parallel.

---

# `ProcessPoolExecutor` limitation: Serialization

- Submitted tasks, i.e callables and data, are sent as pickles to the worker processes.
- Not all objects can be pickled.
  - E.g., lambda or nested functions.

```python
process_executor.submit(lambda x: x * x, 5).result()
```

```
PicklingError: Can't pickle <function <lambda> ...
```

---

# `InterpreterPoolExecutor` limitation: Too new

- The `InterpreterPoolExecutor` is a promising combination of threads without GIL limitation.
- However, it's too new and not all libraries support it.
  - Quite noteably, Numpy lacks support.

```python
interpreter_executor.submit(np.random.randint, 10).result()
```

```text
ImportError: module numpy._core._multiarray_umath does not support loading in subinterpreters
...
IMPORTANT: PLEASE READ THIS FOR ADVICE ON HOW TO SOLVE THIS ISSUE!
```

---

# Resolving serialization issues

- Libraries like `cloudpickle` or `dill` resolve a lot of these limitations.
- Meet our first non-builtin executor: [`joblib/loky`](https://github.com/joblib/loky)
  - > The aim of this project is to provide a robust, cross-platform and cross-version implementation of the `ProcessPoolExecutor` class of `concurrent.futures`.
  - Consistent and robust spawn behaviour
  - Reusable executor
  - Transparent cloudpickle integration

```python
# Create an executor with 4 worker processes, that will
# automatically shutdown after idling for 2s
executor = loky.get_reusable_executor(max_workers=4, timeout=2)
```

- tldr; `loky` is a straightforward replacement for `ProcessPoolExecutor`.

---
layout: two-cols-header
---

# Asyncio: Cooperative multitasking

::left::

- Python `asyncio` is a single-threaded, single-process technique that uses *cooperative multitasking*.
- Coroutines are a central feature of `asyncio`, which can be scheduled concurrently.
- Coroutines can *pause their execution* while waiting for a result.
  - In the meantime, the control is passed to an *event loop*, which can execute another coroutine.
- Event loop is like an infinite loop that monitors coroutines and looks around for things that can be executed.

::right::

<div style="display: flex; justify-content: center;">
  <img src="./asyncio-loop.png" alt="Asyncio event loop" style="width: 600px; max-width: 100%; max-height: 100%;" />
</div>

---

# Asyncio `async`/`await` usage

```python {3-8|10-14|16}
import asyncio

async def get_user_name() -> str:
    await asyncio.sleep(2)  # hand over control to the event loop
    return "Max Planck"

async def get_user_title() -> str:
    await asyncio.sleep(1)  # hand over control to the event loop
    return "Prof."

async def greet() -> None:
    name = await get_user_name()
    title = await get_user_title()
    print(f"Hello, {title} {name}!")

asyncio.run(greet())  # from sync realm to async world
```

---

# `concurrent.futures` within `asyncio`

- `asyncio` cooperative multitasking enables concurrent code using the `async`/`await` syntax.
  - An internal event loop manages the execution of coroutines.
- `asyncio.Future` is similar to `concurrent.futures.Future`.
  - and can be created from `concurrent.futures.Future`:
  ```python
  concurrent_future = executor.submit(do_some_math, 5)
  asyncio_future = asyncio.wrap_future(concurrent_future)
  await asyncio_future
  ```
  - ... or via `loop.run_in_executor`:
  ```python
  loop = asyncio.get_event_loop()
  asyncio_future = loop.run_in_executor(executor, do_some_math, 5)
  ```

- This basically *removes the usual limitation of `asyncio` not supporting CPU-bound tasks*.

---

# Practical data processing usecases with `concurrent.futures` examples

- Quick parallel batch processing, e.g.:
  - Run Pandas pipeline on multiple files.
  - Grid search hyperparameters.
- Non-blocking data processing in a web server or a streaming processor.
  - Even a single-worker executor can enable non-blocking processing.
  - Especially useful for `asyncio` applications.
- Must be careful with resource utilisation, in particular RAM.

---
layout: section
---

# 3. Scaling out: Distributed computing with Dask or Ray

---
layout: two-cols-header
layoutClass: grid-cols-[2fr_1fr]  # Tailwind CSS grid classes
---

# Scaling out: Distributed computing

::left::

- At some point, your calculation may not fit into a single machine.
  - Need to process huge datasets.
  - The calculation is too heavy.
  - Too many repetitions (grid search).
- Memory: "My data do not fit into memory 😱"
  - Symptoms: OOM (Out Of Memory) kills, swapping leading to system freeze.
- Processing power: "My calculation takes too long."
  - Symptoms: CPU, GPU, other PU's at 100%, calculation time too long.
- This is where frameworks like Dask or Ray can help.

::right::

<v-clicks>
<div style="display: flex; justify-content: center;">
  <img src="./cluster.png" alt="Cluster diagram" style="width: 300px; max-width: 100%; max-height: 100%;" />
</div>

</v-clicks>

---

# Checklist before scaling out

- Before spinning up a cluster (and spending 💰💰💰), there are possibilities:
- Profile and possibly optimise your code.
  - Remember the 80:20 Pareto rule.
  - Save either RAM or CPU.
- Data can (sometimes) be memory-mapped.
- Large data can be processed in chunks.
  - This is where executors can help.
- Dask or Ray can help even when running on a single machine.

---
layout: two-cols-header
---

# Dask (Distributed) and Ray

::left::

> [`Dask`](https://docs.dask.org) is a Python library for parallel and distributed computing.
> - Easy to use and set up (it’s just a Python library)
> - Powerful at providing scale, and unlocking complex algorithms
> - and Fun 🎉

- You may know `Dask` for its `DataFrame` pandas-like API.

::right::

> - [Ray](https://docs.ray.io/) is an open-source unified framework for scaling AI and Python applications like machine learning.
> - It provides the compute layer for parallel processing so that you don’t need to be a distributed systems expert.
> - Ray minimizes the complexity of running your distributed individual and end-to-end machine learning workflows ...

- Ray focuses on machine learning and AI workloads.
- [Ray Core](https://docs.ray.io/en/latest/ray-core/walkthrough.html) provides core primitives for distributed computing, similarly to Dask Future API.


---

# `Dask` Futures API is like `concurrent.futures`

- `Dask` supports a `concurrent.futures`-like interface in its [Futures API](https://docs.dask.org/en/stable/futures.html#api).
- This is the foundation for other APIs like Dask arrays and dataframes.
```python
from dask.distributed import Client, as_completed, wait
dask_client = Client()
```

- `dask.Client` API is similar to `concurrent.futures.Executor`.
```python
dask_future = dask_client.submit(do_some_math, 10)
```

- There are substantial differences, e.g. `map` yields a list of futures, not a generator.
  - Hence, `as_completed` or `wait` should be used to iterate over futures as they complete.
  - This is probably more useful than `concurrent.futures`'s `map`.


---

# Dask provides `concurrent.futures` compatibility

- `distributed.client.Future` is *not* compatible with `concurrent.futures.Future`.
  - This will raise an exception:
  ```python
  concurrent.futures.wait([dask_future])
  ```

- A fully compatible `concurrent.futures` executor can be obtained from `Dask`:
```python
executor = dask_client.get_executor()
```

<v-clicks>

- Need to decide whether to work with `Dask`,
  - and profit from its specific features,
- or with `concurrent.futures` and `Dask` as a backend,
  - and profit from the `concurrent.futures` full compatibility, e.g. within `asyncio`.

</v-clicks>

---

# Dask integrates well with `asyncio`

- Dask can operate in `asyncio` mode by using the `asynchronous=True` parameter.
```python
client = await Client(asynchronous=True)
future = client.submit(do_some_math, 5)
result = await future
```

---

# Dask vs concurrent.futures: practical upgrades

<v-clicks>

- **Distributed data & locality**
  - Keep big data on workers with `scatter`/`persist`; schedule tasks where data live.
  - Avoids shipping data through the driver for every task.
- **First-class task dependencies**
  - Pass futures as args to build DAGs; scheduler orders and streams results.
- **Dynamic/nested tasks**
  - Launch tasks from tasks safely via `worker_client` for recursive or fan-out work.
- **Resilience**
  - Automatic retries and recovery from some worker failures.
- **Resource-aware placement**
  - Tag tasks with resources (e.g., `{"GPU": 1}`) for correct scheduling.

</v-clicks>

---

# Dask Demo Time 🙀

1. Start with a problem of a long-running calculation graph: [notebooks/dask_demo_problem.ipynb](./notebooks/dask_demo_problem.ipynb)
2. Solve with Dask: [notebooks/dask_demo_solution.ipynb](./notebooks/dask_demo_solution.ipynb)

Problem flowchart:

```mermaid
flowchart TD
    data[load_data] --> split[split into chunks]

    split --> chunk1[chunk 1]
    split --> chunk2[chunk 2]
    split --> chunkN[chunk N]

    chunk1 --> cd1[check_divisibility]
    chunk2 --> cd2[check_divisibility]
    chunkN --> cdN[check_divisibility]

    cd1 --> cds1a[check_divisibility_single by 3]
    cd1 --> cds1b[check_divisibility_single by 5]
    cd1 --> cds1c[check_divisibility_single by 7]

    cd2 --> cds2a[check_divisibility_single by 3]
    cd2 --> cds2b[check_divisibility_single by 5]
    cd2 --> cds2c[check_divisibility_single by 7]

    cdN --> cdsNa[check_divisibility_single by 3]
    cdN --> cdsNb[check_divisibility_single by 5]
    cdN --> cdsNc[check_divisibility_single by 7]

    cds1a --> and1[logical_and]
    cds1b --> and1
    cds1c --> and1

    cds2a --> and2[logical_and]
    cds2b --> and2
    cds2c --> and2

    cdsNa --> andN[logical_and]
    cdsNb --> andN
    cdsNc --> andN

    and1 --> concat[concatenate]
    and2 --> concat
    andN --> concat

    concat --> result[result]
```


---

# Summary

* Python provides powerful built-in concurrency abstraction and implementation.
  * `concurrent.futures` is a high-level interface for asynchronous execution.
  * `Executor` and `Future` are the main abstractions that other frameworks build upon.
  * Seamlessly employed within `asyncio`
* Dask, Ray and similar provide enhanced features and scaling to distributed computing.
  * Improve pickling, data communication, task dependencies, resilience, resource management, and more.
  * Scale from single machine to large clusters.

* All materials available at [https://github.com/coobas/python-concurrency-fnspe-2025].
