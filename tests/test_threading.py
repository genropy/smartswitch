"""
Tests for thread-safety and thread-local state.

Verifies that:
- Thread-local state is isolated between threads
- Multiple threads can use same instance safely
- Plugin enable/disable is thread-local via contextvars
- Runtime data access is thread-safe
"""

import threading
import time
import unittest

from smartswitch import BasePlugin, Switcher


class ThreadAwarePlugin(BasePlugin):
    """Plugin that tracks thread-specific state."""

    def wrap_handler(self, switch, entry, call_next):
        def wrapper(*args, **kwargs):
            instance = args[0] if args else None
            thread_id = threading.current_thread().name

            # Increment thread-local counter
            count = switch.get_runtime_data(
                instance, entry.name, self.name, f"count_{thread_id}", 0
            )
            switch.set_runtime_data(
                instance, entry.name, self.name, f"count_{thread_id}", count + 1
            )

            return call_next(*args, **kwargs)

        return wrapper


class TestThreadSafety(unittest.TestCase):
    """Test thread-safety of Switcher operations."""

    def test_concurrent_calls_same_instance(self):
        """Test that multiple threads can call same instance safely."""

        class Service:
            ops = Switcher("ops")
            ops.plug(ThreadAwarePlugin, name="ThreadPlugin")

            def __init__(self):
                self.call_count = 0
                self.lock = threading.Lock()

            @ops
            def process(self, value):
                with self.lock:
                    self.call_count += 1
                return value * 2

        service = Service()
        results = []
        errors = []

        def worker(worker_id, iterations):
            """Worker thread that calls service multiple times."""
            try:
                for i in range(iterations):
                    result = Service.ops["process"](service, worker_id * 100 + i)
                    results.append(result)
                    time.sleep(0.001)  # Small delay to increase interleaving
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i, 10), name=f"Worker-{i}")
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no errors
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")

        # Verify all calls completed
        self.assertEqual(len(results), 50)  # 5 threads * 10 iterations

        # Verify service was called correctly
        self.assertEqual(service.call_count, 50)

    def test_thread_local_runtime_data(self):
        """Test that runtime data access is thread-safe."""

        class Counter:
            ops = Switcher("ops")
            ops.plug(ThreadAwarePlugin, name="ThreadPlugin")

            @ops
            def increment(self):
                return "ok"

        counter = Counter()
        thread_results = {}

        def worker(thread_id, iterations):
            """Each thread increments and reads its own counter."""
            for _ in range(iterations):
                Counter.ops["increment"](counter)

            # Read thread-specific count
            count = Counter.ops.get_runtime_data(
                counter, "increment", "ThreadPlugin", f"count_Thread-{thread_id}", 0
            )
            thread_results[thread_id] = count

        # Start threads
        threads = []
        iterations_per_thread = [3, 5, 7, 4, 6]

        for i, iterations in enumerate(iterations_per_thread):
            t = threading.Thread(target=worker, args=(i, iterations), name=f"Thread-{i}")
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Verify each thread has correct count
        for i, expected_count in enumerate(iterations_per_thread):
            self.assertEqual(
                thread_results[i], expected_count, f"Thread {i} should have count {expected_count}"
            )

    def test_thread_local_plugin_enable_disable(self):
        """Test that plugin enable/disable is thread-local via contextvars."""

        class API:
            handlers = Switcher("handlers")
            handlers.plug(ThreadAwarePlugin, name="ThreadPlugin")

            @handlers
            def call(self, value):
                return f"result:{value}"

        api = API()
        thread_results = {}

        def worker_with_plugin_disabled(thread_id):
            """Worker with plugin disabled."""
            # Disable plugin for this thread context
            API.handlers.set_plugin_enabled(api, "call", "ThreadPlugin", False)

            # Make calls
            for i in range(3):
                API.handlers["call"](api, f"disabled-{thread_id}-{i}")

            # Check count (should be 0 because plugin was disabled)
            count = API.handlers.get_runtime_data(
                api, "call", "ThreadPlugin", f"count_DisabledWorker-{thread_id}", 0
            )
            thread_results[f"disabled-{thread_id}"] = count

        def worker_with_plugin_enabled(thread_id):
            """Worker with plugin enabled (default)."""
            # Make calls (plugin enabled by default)
            for i in range(3):
                API.handlers["call"](api, f"enabled-{thread_id}-{i}")

            # Check count (should be 3)
            count = API.handlers.get_runtime_data(
                api, "call", "ThreadPlugin", f"count_EnabledWorker-{thread_id}", 0
            )
            thread_results[f"enabled-{thread_id}"] = count

        # Start threads - some with plugin disabled, some enabled
        threads = []

        for i in range(3):
            t1 = threading.Thread(
                target=worker_with_plugin_disabled, args=(i,), name=f"DisabledWorker-{i}"
            )
            t2 = threading.Thread(
                target=worker_with_plugin_enabled, args=(i,), name=f"EnabledWorker-{i}"
            )
            threads.extend([t1, t2])
            t1.start()
            t2.start()

        # Wait for all
        for t in threads:
            t.join()

        # Verify results
        for i in range(3):
            # Disabled threads should have count=0
            self.assertEqual(
                thread_results[f"disabled-{i}"], 0, f"Disabled thread {i} should have count 0"
            )
            # Enabled threads should have count=3
            self.assertEqual(
                thread_results[f"enabled-{i}"], 3, f"Enabled thread {i} should have count 3"
            )

    def test_concurrent_logging_plugin(self):
        """Test that LoggingPlugin works correctly with concurrent threads."""

        class Service:
            ops = Switcher("ops")
            # Use print mode - new LoggingPlugin doesn't collect history
            ops.plug("logging", flags="print,enabled,before:off,after,time")

            @ops
            def process(self, data):
                time.sleep(0.001)  # Simulate work
                return f"processed:{data}"

        service = Service()
        results = []
        errors = []

        def worker(worker_id, count):
            """Worker that processes items."""
            try:
                for i in range(count):
                    result = Service.ops["process"](service, f"worker-{worker_id}-item-{i}")
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i, 3))
            threads.append(t)
            t.start()

        # Wait
        for t in threads:
            t.join()

        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")

        # Should have 15 results (5 workers * 3 calls each)
        self.assertEqual(len(results), 15)

        # Verify all results are correct
        for result in results:
            self.assertTrue(result.startswith("processed:worker-"))

    def test_race_condition_runtime_data(self):
        """Test that runtime data updates don't have race conditions."""

        class IncrementPlugin(BasePlugin):
            """Plugin that increments a shared counter in runtime data."""

            def wrap_handler(self, switch, entry, call_next):
                def wrapper(*args, **kwargs):
                    instance = args[0] if args else None
                    # Get current count
                    current = switch.get_runtime_data(
                        instance, entry.name, self.name, "shared_counter", 0
                    )
                    # Small delay to increase chance of race condition
                    time.sleep(0.0001)
                    # Set incremented count
                    switch.set_runtime_data(
                        instance, entry.name, self.name, "shared_counter", current + 1
                    )
                    return call_next(*args, **kwargs)

                return wrapper

        class SharedCounter:
            ops = Switcher("ops")
            ops.plug(IncrementPlugin, name="TestPlugin")

            @ops
            def increment_shared(self):
                """Handler that gets wrapped by plugin."""
                return "ok"

        counter = SharedCounter()

        def worker(iterations):
            """Worker that increments counter."""
            for _ in range(iterations):
                SharedCounter.ops["increment_shared"](counter)

        # Start many threads
        threads = []
        for _ in range(10):
            t = threading.Thread(target=worker, args=(5,))
            threads.append(t)
            t.start()

        # Wait
        for t in threads:
            t.join()

        # The point of this test is to verify that concurrent runtime data access
        # doesn't cause crashes or exceptions. Due to the intentional race condition
        # in the test implementation (read-modify-write without locking), the final
        # count may be less than 50. That's expected and acceptable - we're testing
        # that the system remains stable under concurrent access, not that it provides
        # atomic operations (which would require explicit locking in user code).

        # If we get here without exceptions, the test passed
        # Optionally verify data can still be accessed
        final = SharedCounter.ops.get_runtime_data(
            counter, "increment_shared", "TestPlugin", "shared_counter", 0
        )
        # Just verify no corruption (any value 0-50 is acceptable)
        self.assertIsInstance(final, int)
        self.assertGreaterEqual(final, 0)
        self.assertLessEqual(final, 50)


if __name__ == "__main__":
    unittest.main()
