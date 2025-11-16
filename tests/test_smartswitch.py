import unittest

from smartswitch.core import BasePlugin, Switcher


class CountPlugin(BasePlugin):
    def wrap_handler(self, switch, entry, call_next):
        def wrapper(*args, **kwargs):
            instance = args[0] if args else None
            count = switch.get_runtime_data(instance, entry.name, self.name, "count", 0)
            switch.set_runtime_data(instance, entry.name, self.name, "count", count + 1)
            return call_next(*args, **kwargs)

        return wrapper


class MetaPlugin(BasePlugin):
    def on_decore(self, switch, func, entry):
        entry.metadata["decorated"] = True


class TracePlugin(BasePlugin):
    def on_decore(self, switch, func, entry):
        label = self.config.get("label", self.name)
        entry.metadata.setdefault("trace", []).append(label)


class FlagPlugin(BasePlugin):
    def on_decore(self, switch, func, entry):
        entry.metadata["flagged"] = True


class GatePlugin(BasePlugin):
    def wrap_handler(self, switch, entry, call_next):
        def wrapper(*args, **kwargs):
            config = self.get_config(entry.name)
            if config.get("blocked"):
                raise RuntimeError("blocked by GatePlugin")
            return call_next(*args, **kwargs)

        return wrapper


class Base:
    main = Switcher("main", prefix="do_")
    main.plug(CountPlugin)
    main.plug(MetaPlugin)


class Child(Base):
    child = Switcher("child", parent=Base.main)

    @Base.main
    def do_run(self, x):
        return f"run:{x}"

    @Base.main("special")
    def do_special(self, x):
        return f"special:{x}"

    @child
    def do_child(self, x):
        return f"child:{x}"


class TestSwitcher(unittest.TestCase):
    def test_prefix_and_alias_registration(self):
        desc = Child.main.describe()
        self.assertIn("run", desc["methods"])
        self.assertIn("special", desc["methods"])
        self.assertNotIn("do_run", desc["methods"])
        self.assertTrue(desc["methods"]["run"]["metadata_keys"])
        # collision check
        with self.assertRaises(ValueError):

            @Child.main
            def do_run(self, x):
                return x  # name "run" already used

    def test_named_dispatch(self):
        obj = Child()
        self.assertEqual(Child.main["run"](obj, 5), "run:5")
        self.assertEqual(Child.main["special"](obj, 7), "special:7")

    def test_dotted_path_dispatch(self):
        obj = Child()
        # child switch is attached under main; we name it "child"
        Child.main.add_child(Child.child, name="child")
        self.assertEqual(Child.main["child.child"](obj, 3), "child:3")

    def test_plugin_runtime_count(self):
        obj = Child()
        # Get initial count (may not be 0 on Windows due to ID reuse)
        initial_count = Child.main.get_runtime_data(obj, "run", "CountPlugin", "count", 0)
        Child.main["run"](obj, 1)
        Child.main["run"](obj, 2)
        final_count = Child.main.get_runtime_data(obj, "run", "CountPlugin", "count", 0)
        # Verify count incremented by 2, not absolute value
        self.assertEqual(final_count - initial_count, 2)

    def test_plugin_enable_disable(self):
        obj = Child()
        # disable CountPlugin for run on this instance
        Child.main.set_plugin_enabled(obj, "run", "CountPlugin", False)
        Child.main["run"](obj, 1)
        count = Child.main.get_runtime_data(obj, "run", "CountPlugin", "count", 0)
        self.assertEqual(count, 0)
        # re-enable for other tests
        Child.main.set_plugin_enabled(obj, "run", "CountPlugin", True)

    def test_instance_plugin_disable_and_runtime_data(self):
        obj = Child()
        Child.main.set_runtime_data(obj, "run", "CountPlugin", "extra", "before")
        Child.main.set_plugin_enabled(obj, "run", "CountPlugin", False)
        try:
            Child.main["run"](obj, 1)
            count = Child.main.get_runtime_data(obj, "run", "CountPlugin", "count", 0)
            self.assertEqual(count, 0)
            self.assertEqual(
                Child.main.get_runtime_data(obj, "run", "CountPlugin", "extra"), "before"
            )
        finally:
            Child.main.set_plugin_enabled(obj, "run", "CountPlugin", True)

    def test_runtime_data_defaults(self):
        obj = Child()
        Child.main.set_runtime_data(obj, "run", "CountPlugin", "custom", 42)
        self.assertEqual(Child.main.get_runtime_data(obj, "run", "CountPlugin", "custom"), 42)
        self.assertEqual(
            Child.main.get_runtime_data(obj, "run", "CountPlugin", "missing", default=-1), -1
        )

    def test_use_parent_plugins_stack(self):
        class Parent:
            root = Switcher("root")
            root.plug(TracePlugin, name="TraceParent", label="parent")

        class ChildOwner(Parent):
            branch = Switcher("branch", parent=Parent.root, inherit_plugins=True)

            @branch
            def do_branch(self):
                return "branch"

        entry = ChildOwner.branch._methods["do_branch"]
        self.assertEqual(entry.plugins, ["TraceParent"])
        self.assertEqual(entry.metadata["trace"], ["parent"])

    def test_plug_breaks_use_parent_mode(self):
        class Parent:
            root = Switcher("root")
            root.plug(TracePlugin, name="TraceParent", label="parent")

        class ChildOwner(Parent):
            branch = Switcher("branch", parent=Parent.root, inherit_plugins=True)
            branch.plug(TracePlugin, name="TraceChild", label="child")

            @branch
            def do_branch(self):
                return "branch"

        entry = ChildOwner.branch._methods["do_branch"]
        self.assertEqual(entry.plugins, ["TraceChild"])
        self.assertEqual(entry.metadata["trace"], ["child"])

    def test_copy_plugins_from_parent(self):
        class Parent:
            root = Switcher("root")
            root.plug(TracePlugin, name="TraceParent", label="parent")

        class ChildOwner(Parent):
            branch = Switcher("branch", parent=Parent.root, inherit_plugins=False)
            branch.copy_plugins_from_parent()
            branch.plug(TracePlugin, name="TraceChild", label="child")

            @branch
            def do_branch(self):
                return "branch"

        entry = ChildOwner.branch._methods["do_branch"]
        self.assertEqual(entry.plugins, ["TraceParent", "TraceChild"])
        self.assertEqual(entry.metadata["trace"], ["parent", "child"])

    def test_register_plugin_by_name(self):
        Switcher.register_plugin("flag", FlagPlugin)
        try:

            class Owner:
                switch = Switcher("switch")
                switch.plug("flag")

                @switch
                def do_work(self):
                    return "ok"

            entry = Owner.switch._methods["do_work"]
            self.assertIn("flag", entry.plugins)
            self.assertTrue(entry.metadata["flagged"])
        finally:
            Switcher._global_plugin_registry.pop("flag", None)

    def test_unknown_registered_plugin_raises(self):
        switch = Switcher("switch")
        with self.assertRaises(ValueError):
            switch.plug("missing")

    def test_plugin_config_per_method(self):
        class Owner:
            gate = Switcher("gate")
            gate.plug(GatePlugin)

            @gate
            def do_run(self, x):
                return f"run:{x}"

            @gate
            def do_block(self, x):
                return f"block:{x}"

        Owner.gate.plugin("GatePlugin").configure["do_block"].blocked = True
        obj = Owner()
        self.assertEqual(Owner.gate["do_run"](obj, 1), "run:1")
        with self.assertRaises(RuntimeError):
            Owner.gate["do_block"](obj, 2)

    def test_plugin_config_enabled_flag(self):
        class Owner:
            gate = Switcher("gate")
            gate.plug(GatePlugin)

            @gate
            def do_stable(self, x):
                return f"stable:{x}"

        Owner.gate.plugin("GatePlugin").configure.blocked = True
        owner = Owner()
        with self.assertRaises(RuntimeError):
            Owner.gate["do_stable"](owner, 1)
        Owner.gate.plugin("GatePlugin").configure["do_stable"].enabled = False
        self.assertEqual(Owner.gate["do_stable"](owner, 2), "stable:2")

    def test_add_child_discovers_switchers_on_object(self):
        root = Switcher("root")

        class Module:
            api = Switcher("module")

        module = Module()
        root.add_child(module)
        self.assertIs(Module.api.parent, root)
        self.assertIs(root.get_child("module"), Module.api)

    def test_add_child_handles_instance_defined_switcher(self):
        root = Switcher("root")

        class DynamicModule:
            def __init__(self):
                self.inner = Switcher("inner")

        module = DynamicModule()
        root.add_child(module)
        self.assertIs(module.inner.parent, root)
        self.assertIs(root.get_child("inner"), module.inner)

    def test_add_child_raises_for_objects_without_switchers(self):
        root = Switcher("root")
        with self.assertRaises(TypeError):
            root.add_child(object())

    def test_add_child_raises_when_switch_has_other_parent(self):
        root_a = Switcher("root_a")
        root_b = Switcher("root_b")
        child = Switcher("child", parent=root_a)
        with self.assertRaises(ValueError):
            root_b.add_child(child)

    def test_add_child_discovers_multiple_switchers(self):
        root = Switcher("root")

        class Module:
            alpha = Switcher("alpha")
            beta = Switcher("beta")

        module = Module()
        root.add_child(module)
        self.assertIs(root.get_child("alpha"), Module.alpha)
        self.assertIs(root.get_child("beta"), Module.beta)

    def test_add_child_uses_attribute_name_for_anonymous_switch(self):
        root = Switcher("root")

        class Module:
            anonymous = Switcher()

        module = Module()
        module.anonymous.name = None
        root.add_child(module)
        self.assertIs(root.get_child("anonymous"), module.anonymous)

    def test_add_child_deduplicates_shared_switch_references(self):
        root = Switcher("root")

        class Module:
            shared = Switcher("shared")

            def __init__(self):
                self.alias = self.shared

        module = Module()
        root.add_child(module)
        self.assertIs(root.get_child("shared"), module.shared)


if __name__ == "__main__":
    unittest.main()
