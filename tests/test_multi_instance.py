"""
Tests for multiple instance isolation.

Verifies that:
- Multiple instances have separate state
- Runtime data is per-instance
- Plugin enable/disable is per-instance
- Logging history is per-instance
"""

import unittest

from smartswitch import BasePlugin, Switcher


class CounterPlugin(BasePlugin):
    """Plugin that counts calls per instance."""

    def wrap_handler(self, switch, entry, call_next):
        def wrapper(*args, **kwargs):
            instance = args[0] if args else None
            count = switch.get_runtime_data(instance, entry.name, self.name, "count", 0)
            switch.set_runtime_data(instance, entry.name, self.name, "count", count + 1)
            return call_next(*args, **kwargs)

        return wrapper


class TestMultipleInstances(unittest.TestCase):
    """Test state isolation across multiple instances."""

    def test_separate_runtime_data_per_instance(self):
        """Test that each instance has separate runtime data."""

        class Shop:
            ops = Switcher("ops")
            ops.plug(CounterPlugin)

            def __init__(self, name):
                self.name = name

            @ops
            def process(self, value):
                return f"{self.name}:{value}"

        shop1 = Shop("shop1")
        shop2 = Shop("shop2")
        shop3 = Shop("shop3")

        # Each shop calls process different number of times
        Shop.ops["process"](shop1, "A")
        Shop.ops["process"](shop1, "B")

        Shop.ops["process"](shop2, "X")
        Shop.ops["process"](shop2, "Y")
        Shop.ops["process"](shop2, "Z")

        Shop.ops["process"](shop3, "1")

        # Verify separate counts
        count1 = Shop.ops.get_runtime_data(shop1, "process", "CounterPlugin", "count", 0)
        count2 = Shop.ops.get_runtime_data(shop2, "process", "CounterPlugin", "count", 0)
        count3 = Shop.ops.get_runtime_data(shop3, "process", "CounterPlugin", "count", 0)

        self.assertEqual(count1, 2)
        self.assertEqual(count2, 3)
        self.assertEqual(count3, 1)

    def test_plugin_enable_disable_per_instance(self):
        """Test that plugin enable/disable is per-instance."""

        class Service:
            api = Switcher("api")
            api.plug(CounterPlugin)

            def __init__(self, service_id):
                self.service_id = service_id

            @api
            def call(self, data):
                return f"service_{self.service_id}:{data}"

        svc1 = Service(1)
        svc2 = Service(2)

        # Disable plugin for svc1 only
        Service.api.set_plugin_enabled(svc1, "call", "CounterPlugin", False)

        # Both call the method
        Service.api["call"](svc1, "test1")
        Service.api["call"](svc2, "test2")

        # svc1 should have count=0 (plugin disabled)
        # svc2 should have count=1 (plugin enabled)
        count1 = Service.api.get_runtime_data(svc1, "call", "CounterPlugin", "count", 0)
        count2 = Service.api.get_runtime_data(svc2, "call", "CounterPlugin", "count", 0)

        self.assertEqual(count1, 0)  # Plugin was disabled
        self.assertEqual(count2, 1)  # Plugin was enabled

    def test_custom_runtime_data_per_instance(self):
        """Test that custom runtime data is isolated per instance."""

        class Worker:
            tasks = Switcher("tasks")
            tasks.plug(CounterPlugin)

            def __init__(self, worker_id):
                self.worker_id = worker_id

            @tasks
            def work(self, task):
                return f"worker_{self.worker_id}:{task}"

        w1 = Worker(1)
        w2 = Worker(2)
        w3 = Worker(3)

        # Set custom data per worker
        Worker.tasks.set_runtime_data(w1, "work", "CounterPlugin", "status", "active")
        Worker.tasks.set_runtime_data(w2, "work", "CounterPlugin", "status", "paused")
        Worker.tasks.set_runtime_data(w3, "work", "CounterPlugin", "status", "active")

        Worker.tasks.set_runtime_data(w1, "work", "CounterPlugin", "priority", "high")
        Worker.tasks.set_runtime_data(w2, "work", "CounterPlugin", "priority", "low")

        # Verify isolated data
        self.assertEqual(
            Worker.tasks.get_runtime_data(w1, "work", "CounterPlugin", "status"), "active"
        )
        self.assertEqual(
            Worker.tasks.get_runtime_data(w2, "work", "CounterPlugin", "status"), "paused"
        )
        self.assertEqual(
            Worker.tasks.get_runtime_data(w3, "work", "CounterPlugin", "status"), "active"
        )

        self.assertEqual(
            Worker.tasks.get_runtime_data(w1, "work", "CounterPlugin", "priority"), "high"
        )
        self.assertEqual(
            Worker.tasks.get_runtime_data(w2, "work", "CounterPlugin", "priority"), "low"
        )
        # w3 has no priority set
        self.assertIsNone(Worker.tasks.get_runtime_data(w3, "work", "CounterPlugin", "priority"))

    def test_multiple_plugins_per_instance_control(self):
        """Test controlling multiple plugins independently per instance."""

        class API:
            handlers = Switcher("handlers")
            handlers.plug(CounterPlugin, name="Counter1")
            handlers.plug(CounterPlugin, name="Counter2")

            def __init__(self, api_name):
                self.api_name = api_name

            @handlers
            def endpoint(self, request):
                return f"{self.api_name}:{request}"

        api1 = API("api1")
        api2 = API("api2")

        # Disable Counter1 for api1, Counter2 for api2
        API.handlers.set_plugin_enabled(api1, "endpoint", "Counter1", False)
        API.handlers.set_plugin_enabled(api2, "endpoint", "Counter2", False)

        # Call endpoints
        API.handlers["endpoint"](api1, "req1")
        API.handlers["endpoint"](api2, "req2")

        # api1: Counter1=0 (disabled), Counter2=1 (enabled)
        # api2: Counter1=1 (enabled), Counter2=0 (disabled)

        c1_count1 = API.handlers.get_runtime_data(api1, "endpoint", "Counter1", "count", 0)
        c2_count1 = API.handlers.get_runtime_data(api1, "endpoint", "Counter2", "count", 0)

        c1_count2 = API.handlers.get_runtime_data(api2, "endpoint", "Counter1", "count", 0)
        c2_count2 = API.handlers.get_runtime_data(api2, "endpoint", "Counter2", "count", 0)

        self.assertEqual(c1_count1, 0)  # Disabled for api1
        self.assertEqual(c2_count1, 1)  # Enabled for api1

        self.assertEqual(c1_count2, 1)  # Enabled for api2
        self.assertEqual(c2_count2, 0)  # Disabled for api2


if __name__ == "__main__":
    unittest.main()
