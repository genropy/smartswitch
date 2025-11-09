"""
SmartSwitch - Intelligent rule-based function dispatch for Python.

Optimized version with ~3x performance improvement over naive implementation.
"""

import inspect
from functools import partial
from typing import Any, Union, get_args, get_origin


class BoundSwitcher:
    """
    A bound version of Switcher that automatically binds 'self' to retrieved handlers.
    Created when accessing a Switcher instance as a class attribute.
    """

    __slots__ = ("_switcher", "_instance")

    def __init__(self, switcher, instance):
        self._switcher = switcher
        self._instance = instance

    def __call__(self, name):
        """
        Get a handler by name and bind it to the instance.
        Supports dot notation for hierarchical navigation.

        Args:
            name: Handler function name (supports dot notation like 'child.handler')

        Returns:
            Bound method ready to call without passing self
        """
        # Check for dot notation (hierarchical navigation)
        if '.' in name:
            # Delegate to underlying Switcher's dot notation support
            # which returns the handler, then bind it
            handler = self._switcher(name)
            # If it's already a HandlerOrDecorator, extract the actual function
            if hasattr(handler, '__self__'):
                # Already bound
                return handler
            # Bind to instance
            bound = partial(handler, self._instance)
            # Preserve __wrapped__ if available
            if hasattr(handler, '__wrapped__'):
                bound.__wrapped__ = handler.__wrapped__
            return bound

        # Standard lookup
        func = self._switcher._handlers[name]
        bound = partial(func, self._instance)
        # Add __wrapped__ attribute for introspection
        bound.__wrapped__ = func
        return bound


class Switcher:
    """
    Intelligent function dispatch based on type and value rules.

    Supports three modes:
    1. Dispatch by name: switch("handler_name")
    2. Automatic dispatch: switch()(args) - chooses handler by rules
    3. Both: register with name, dispatch automatically

    Optimizations applied:
    - Cached signature inspection (done once per function)
    - Manual kwargs building (no expensive bind_partial)
    - Pre-compiled type checkers
    - __slots__ for reduced memory overhead
    """

    __slots__ = (
        "name",
        "description",
        "prefix",
        "_parent",
        "_children",
        "_handlers",
        "_rules",
        "_default_handler",
        "_param_names_cache",
    )

    def __init__(
        self,
        name: str = "default",
        description: str | None = None,
        prefix: str | None = None,
        parent: "Switcher | None" = None,
    ):
        """
        Initialize a new Switcher.

        Args:
            name: Optional name for this switch (for debugging)
            description: Optional description for documentation/introspection
            prefix: If set, auto-derive handler names by removing this prefix
                    from decorated function names
            parent: Optional parent Switcher for hierarchical API structure
        """
        self.name = name
        self.description = description
        self.prefix = prefix
        self._parent = None
        self._children = set()
        self._handlers = {}  # name -> function mapping
        self._rules = []  # list of (matcher, function) tuples
        self._default_handler = None  # default catch-all handler
        self._param_names_cache = {}  # function -> param names cache

        # Set parent after initialization (triggers property setter)
        if parent is not None:
            self.parent = parent

    def __call__(
        self,
        arg: Any = None,
        *,
        typerule: dict[str, type] | None = None,
        valrule: Any = None,
    ) -> Any:
        """
        Multi-purpose call method supporting different invocation patterns.

        Patterns:
        1. @switch                    -> register as default handler
        2. @switch('alias')           -> register with custom name
        3. @switch(typerule=..., valrule=...) -> register with rules
        4. switch("name")            -> get handler by name
        5. switch()                  -> get dispatcher function

        Args:
            arg: Function to decorate, handler name, or None for dispatcher
            typerule: Dict mapping parameter names to expected types
            valrule: Callable that receives **kwargs and returns bool

        Returns:
            Decorated function, handler, or dispatcher depending on usage
        """
        # Case 1: @switch (decorator without parameters - default handler)
        if callable(arg) and typerule is None and valrule is None:
            # Derive handler name (with optional prefix stripping)
            if self.prefix and arg.__name__.startswith(self.prefix):
                handler_name = arg.__name__[len(self.prefix) :]
            else:
                handler_name = arg.__name__

            # Check for duplicates
            if handler_name in self._handlers:
                existing = self._handlers[handler_name]
                raise ValueError(
                    f"Handler '{handler_name}' already taken by function '{existing.__name__}'"
                )

            self._handlers[handler_name] = arg
            self._default_handler = arg
            return arg

        # Case 2: @switch('alias') - register with custom name OR lookup
        if isinstance(arg, str) and typerule is None and valrule is None:
            # Check for dot notation (hierarchical navigation)
            if '.' in arg:
                parts = arg.split('.', 1)
                child_name = parts[0]
                remaining = parts[1]

                # Find child by name
                for child in self._children:
                    if child.name == child_name:
                        # Recursively navigate
                        return child(remaining)

                # Child not found
                raise KeyError(f"Child Switcher '{child_name}' not found")

            # No dot notation - standard behavior
            # If handler exists, check if being used as decorator or lookup
            if arg in self._handlers:
                handler = self._handlers[arg]

                # Create a wrapper that can be used both ways
                class HandlerOrDecorator:
                    def __call__(self, *args, **kwargs):
                        # If called with a function as first arg and it's callable,
                        # assume decorator usage
                        if len(args) == 1 and callable(args[0]) and not kwargs:
                            # Check if it looks like it's being used as decorator
                            # (single callable argument, no other args)
                            import inspect

                            if inspect.isfunction(args[0]) or inspect.ismethod(args[0]):
                                raise ValueError(f"Alias '{arg}' is already registered")
                        # Normal function call
                        return handler(*args, **kwargs)

                wrapper = HandlerOrDecorator()
                # Add __wrapped__ attribute for introspection tools
                wrapper.__wrapped__ = handler
                return wrapper

            # Not found, return decorator for registration
            def decorator(func):
                self._handlers[arg] = func
                return func

            return decorator

        # Case 3: @switch(typerule=..., valrule=...) - returns decorator
        if typerule is not None or valrule is not None:
            # Detect valrule calling convention
            valrule_takes_dict = False
            valrule_needs_unpack = False  # True for **kw style
            if valrule is not None:
                valrule_sig = inspect.signature(valrule)
                params = valrule_sig.parameters

                # Compact dict syntax comes in two forms:
                # 1. Single positional param named 'kw', 'kwargs', or 'args'
                #    e.g., lambda kw: kw['mode'] == 'test'
                #    Call with: valrule(args_dict)
                # 2. VAR_KEYWORD parameter (**kw)
                #    e.g., lambda **kw: kw.get('mode') == 'test'
                #    Call with: valrule(**args_dict)

                positional_params = [
                    name
                    for name, p in params.items()
                    if p.kind
                    not in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
                ]
                has_var_keyword = any(
                    p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
                )

                if len(positional_params) == 1 and list(positional_params)[0] in (
                    "kw",
                    "kwargs",
                    "args",
                ):
                    valrule_takes_dict = True
                    valrule_needs_unpack = False
                elif has_var_keyword and len(positional_params) == 0:
                    valrule_takes_dict = True
                    valrule_needs_unpack = True

            def decorator(func):
                # OPTIMIZATION: Cache signature once
                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())
                self._param_names_cache[func] = param_names

                # OPTIMIZATION: Pre-compile type checks
                if typerule:
                    type_checks = self._compile_type_checks(typerule, param_names)
                else:
                    type_checks = None

                # OPTIMIZATION: Optimized matcher - no bind_partial
                def matches(*a, **kw):
                    # Build args dict manually (much faster than bind_partial)
                    args_dict = {}
                    for i, name in enumerate(param_names):
                        if i < len(a):
                            args_dict[name] = a[i]
                        elif name in kw:
                            args_dict[name] = kw[name]

                    # Type checks
                    if type_checks:
                        for name, checker in type_checks:
                            if name in args_dict and not checker(args_dict[name]):
                                return False

                    # Value rule - support both calling conventions
                    if valrule:
                        if valrule_takes_dict:
                            # Compact syntax
                            if valrule_needs_unpack:
                                # lambda **kw: kw.get('x') > 10
                                if not valrule(**args_dict):
                                    return False
                            else:
                                # lambda kw: kw['x'] > 10
                                if not valrule(args_dict):
                                    return False
                        else:
                            # Expanded syntax: lambda x, y: x > 10
                            if not valrule(**args_dict):
                                return False

                    return True

                self._rules.append((matches, func))
                # Register by name so it can be retrieved with sw('name')
                self._handlers[func.__name__] = func
                return func

            return decorator

        # Case 4: switch() - invoker
        if arg is None:

            def invoker(*a, **kw):
                # Check specific rules first
                for cond, func in self._rules:
                    if cond(*a, **kw):
                        return func(*a, **kw)
                # Check default last
                if self._default_handler:
                    return self._default_handler(*a, **kw)
                raise ValueError(f"No rule matched for {a}, {kw}")

            return invoker

        raise TypeError("Switcher.__call__ expects callable, str, or None")

    def __get__(self, instance: Any, owner: type | None = None) -> "Switcher | BoundSwitcher":
        """
        Descriptor protocol support for automatic method binding.

        When a Switcher is accessed as a class attribute, this returns
        a BoundSwitcher that automatically binds 'self' to retrieved handlers.

        Args:
            instance: The instance accessing this descriptor
            owner: The class owning this descriptor

        Returns:
            BoundSwitcher if accessed from instance, self if accessed from class
        """
        if instance is None:
            # Accessed from class, return the switcher itself
            return self
        # Accessed from instance, return bound version
        return BoundSwitcher(self, instance)

    def _compile_type_checks(self, typerule, param_names):
        """
        Pre-compile type checkers for faster runtime evaluation.

        Args:
            typerule: Dict mapping parameter names to types
            param_names: List of parameter names from function signature

        Returns:
            List of (param_name, checker_function) tuples
        """
        checks = []
        for name, hint in typerule.items():
            if name not in param_names:
                continue

            # Create optimized checker for this type
            checker = self._make_type_checker(hint)
            checks.append((name, checker))

        return checks

    def _make_type_checker(self, hint):
        """
        Create an optimized type checking function.

        Args:
            hint: Type hint to check against

        Returns:
            Function that takes a value and returns bool
        """
        # Fast path for Any
        if hint is Any:
            return lambda val: True

        origin = get_origin(hint)

        # Union types (e.g., int | str)
        if origin is Union:
            args = get_args(hint)
            # Pre-compile checkers for each union member
            checkers = [self._make_type_checker(t) for t in args]
            return lambda val: any(c(val) for c in checkers)

        # Simple type check
        return lambda val: isinstance(val, hint)

    def entries(self):
        """
        List all registered handler names.

        Returns:
            List of handler names registered in this Switcher
        """
        return list(self._handlers.keys())

    @property
    def parent(self) -> "Switcher | None":
        """
        Get the parent Switcher.

        Returns:
            Parent Switcher instance or None if no parent
        """
        return self._parent

    @parent.setter
    def parent(self, value: "Switcher | None"):
        """
        Set the parent Switcher with automatic bidirectional registration.

        When setting a parent:
        1. Unregisters from old parent (if any)
        2. Sets new parent
        3. Registers with new parent's children

        Args:
            value: Parent Switcher instance or None to unset parent
        """
        # Unregister from old parent
        if self._parent is not None:
            self._parent._children.discard(self)

        # Set new parent
        self._parent = value

        # Register with new parent
        if value is not None:
            value._children.add(self)

    @property
    def children(self) -> set["Switcher"]:
        """
        Get all child Switchers.

        Returns:
            Set of child Switcher instances
        """
        return self._children.copy()

    def add_child(self, switcher: "Switcher") -> "Switcher":
        """
        Add a child Switcher and return it.

        This also sets this Switcher as the child's parent.
        Returns the child so it can be used as a decorator.

        Args:
            switcher: Child Switcher to add

        Returns:
            The child Switcher (for chaining/assignment)

        Raises:
            TypeError: If switcher is not a Switcher instance
        """
        if not isinstance(switcher, Switcher):
            raise TypeError(f"Expected Switcher instance, got {type(switcher)}")

        # Setting parent will automatically add to children via property setter
        switcher.parent = self
        return switcher

    def add(self, switcher: "Switcher") -> "Switcher":
        """
        Alias for add_child(). Add a child Switcher and return it.

        This is a shorter, more convenient alias for add_child().

        Args:
            switcher: Child Switcher to add

        Returns:
            The child Switcher (for chaining/assignment)
        """
        return self.add_child(switcher)

    def remove_child(self, switcher: "Switcher"):
        """
        Remove a child Switcher.

        This also unsets the child's parent.

        Args:
            switcher: Child Switcher to remove
        """
        if switcher in self._children:
            # Setting parent to None will automatically remove from children
            switcher.parent = None
