"""
Comprehensive test suite for SmartSwitch.

Tests cover all major functionality:
- Type-based dispatch
- Value-based dispatch
- Combined rules
- Named handler lookup
- Automatic dispatch
- Descriptor protocol
- Error handling
- Edge cases
"""
import pytest
from typing import Union, Any
from smartswitch import Switcher


class TestBasicSwitcher:
    """Test basic Switcher creation and properties."""

    def test_create_switcher(self):
        """Test creating a basic switcher."""
        sw = Switcher()
        assert sw.name == "default"
        assert sw._handlers == {}
        assert sw._rules == []
        assert sw._default_handler is None

    def test_create_named_switcher(self):
        """Test creating a switcher with a custom name."""
        sw = Switcher(name="my_switch")
        assert sw.name == "my_switch"


class TestDecoratorPatterns:
    """Test different decorator usage patterns."""

    def test_default_handler_decorator(self):
        """Test @sw decorator without arguments."""
        sw = Switcher()

        @sw
        def handler(x):
            return f"default: {x}"

        assert sw._default_handler == handler
        assert "handler" in sw._handlers

    def test_typerule_decorator(self):
        """Test @sw(typerule=...) decorator."""
        sw = Switcher()

        @sw(typerule={'x': int})
        def handler(x):
            return f"int: {x}"

        assert len(sw._rules) == 1
        assert "handler" in sw._handlers

    def test_valrule_decorator(self):
        """Test @sw(valrule=...) decorator."""
        sw = Switcher()

        @sw(valrule=lambda x: x > 0)
        def handler(x):
            return "positive"

        assert len(sw._rules) == 1
        assert "handler" in sw._handlers

    def test_combined_rules_decorator(self):
        """Test @sw(typerule=..., valrule=...) decorator."""
        sw = Switcher()

        @sw(typerule={'x': int}, valrule=lambda x: x > 0)
        def handler(x):
            return "positive int"

        assert len(sw._rules) == 1
        assert "handler" in sw._handlers


class TestTypeRules:
    """Test type-based dispatch."""

    def test_simple_type_dispatch(self):
        """Test dispatching based on single type."""
        sw = Switcher()

        @sw(typerule={'x': str})
        def handle_string(x):
            return "string"

        @sw(typerule={'x': int})
        def handle_int(x):
            return "int"

        @sw
        def handle_default(x):
            return "default"

        assert sw()(x="hello") == "string"
        assert sw()(x=42) == "int"
        assert sw()(x=3.14) == "default"

    def test_union_type_dispatch(self):
        """Test dispatching with Union types."""
        sw = Switcher()

        @sw(typerule={'x': int | float})
        def handle_number(x):
            return "number"

        @sw(typerule={'x': str})
        def handle_string(x):
            return "string"

        assert sw()(x=42) == "number"
        assert sw()(x=3.14) == "number"
        assert sw()(x="hi") == "string"

    def test_multiple_parameters_type_rules(self):
        """Test type rules with multiple parameters."""
        sw = Switcher()

        @sw(typerule={'a': int, 'b': int})
        def add_ints(a, b):
            return a + b

        @sw(typerule={'a': str, 'b': str})
        def concat_strings(a, b):
            return a + b

        assert sw()(a=5, b=10) == 15
        assert sw()(a="hello", b=" world") == "hello world"

    def test_custom_class_type_dispatch(self):
        """Test dispatching with custom classes."""
        class Person:
            def __init__(self, name):
                self.name = name

        class Company:
            def __init__(self, name):
                self.name = name

        sw = Switcher()

        @sw(typerule={'entity': Person})
        def handle_person(entity):
            return f"person: {entity.name}"

        @sw(typerule={'entity': Company})
        def handle_company(entity):
            return f"company: {entity.name}"

        person = Person("Alice")
        company = Company("Acme")

        assert sw()(entity=person) == "person: Alice"
        assert sw()(entity=company) == "company: Acme"


class TestValueRules:
    """Test value-based dispatch."""

    def test_simple_value_rule(self):
        """Test dispatching based on value condition."""
        sw = Switcher()

        @sw(valrule=lambda x: x < 0)
        def handle_negative(x):
            return "negative"

        @sw(valrule=lambda x: x > 0)
        def handle_positive(x):
            return "positive"

        @sw(valrule=lambda x: x == 0)
        def handle_zero(x):
            return "zero"

        assert sw()(x=-5) == "negative"
        assert sw()(x=5) == "positive"
        assert sw()(x=0) == "zero"

    def test_value_rule_with_multiple_params(self):
        """Test value rules with multiple parameters."""
        sw = Switcher()

        @sw(valrule=lambda a, b: a > b)
        def handle_greater(a, b):
            return f"{a} > {b}"

        @sw(valrule=lambda a, b: a < b)
        def handle_less(a, b):
            return f"{a} < {b}"

        @sw(valrule=lambda a, b: a == b)
        def handle_equal(a, b):
            return f"{a} == {b}"

        assert sw()(a=10, b=5) == "10 > 5"
        assert sw()(a=3, b=7) == "3 < 7"
        assert sw()(a=5, b=5) == "5 == 5"

    def test_complex_value_rule(self):
        """Test complex value conditions."""
        sw = Switcher()

        @sw(valrule=lambda x: 0 <= x <= 100)
        def handle_percentage(x):
            return "percentage"

        @sw(valrule=lambda x: x > 100)
        def handle_large(x):
            return "large"

        @sw
        def handle_other(x):
            return "other"

        assert sw()(x=50) == "percentage"
        assert sw()(x=150) == "large"
        assert sw()(x=-10) == "other"


class TestCompactLambdaSyntax:
    """Test compact lambda syntax with dict parameter."""

    def test_compact_lambda_single_param(self):
        """Test lambda kw: kw['x'] syntax."""
        sw = Switcher()

        @sw(valrule=lambda kw: kw['mode'] == 'test')
        def handle_test(mode):
            return "test mode"

        @sw(valrule=lambda kw: kw['mode'] == 'prod')
        def handle_prod(mode):
            return "prod mode"

        @sw
        def handle_default(mode):
            return "default"

        assert sw()(mode='test') == "test mode"
        assert sw()(mode='prod') == "prod mode"
        assert sw()(mode='other') == "default"

    def test_compact_lambda_multiple_params(self):
        """Test lambda kw: with multiple parameter conditions."""
        sw = Switcher()

        @sw(valrule=lambda kw: kw['mode'] == 'xxx' and kw['height'] > 30)
        def handle_high(mode, height):
            return f"High: {height}"

        @sw(valrule=lambda kw: kw['height'] <= 30)
        def handle_low(mode, height):
            return f"Low: {height}"

        assert sw()(mode='xxx', height=50) == "High: 50"
        assert sw()(mode='xxx', height=20) == "Low: 20"

    def test_compact_lambda_with_kw_get(self):
        """Test lambda kw: kw.get() syntax."""
        sw = Switcher()

        @sw(valrule=lambda kw: kw.get('status') == 'active')
        def handle_active(status):
            return "active"

        @sw
        def handle_default(status):
            return "default"

        assert sw()(status='active') == "active"
        assert sw()(status='other') == "default"

    def test_mixed_compact_and_expanded_syntax(self):
        """Test mixing compact and expanded lambda syntax."""
        sw = Switcher()

        @sw(valrule=lambda kw: kw['x'] > 100)  # Compact
        def handle_large(x):
            return "large"

        @sw(valrule=lambda x: x > 50)  # Expanded
        def handle_medium(x):
            return "medium"

        @sw(valrule=lambda kw: kw['x'] > 0)  # Compact
        def handle_small(x):
            return "small"

        assert sw()(x=150) == "large"
        assert sw()(x=75) == "medium"
        assert sw()(x=25) == "small"

    def test_var_keyword_lambda_syntax(self):
        """Test lambda **kw: syntax (VAR_KEYWORD)."""
        sw = Switcher()

        @sw(valrule=lambda **kw: kw.get('y', 0) > 5)
        def handle_with_y(x, y=0):
            return f"y={y}"

        @sw
        def handle_default(x, y=0):
            return "default"

        assert sw()(x=1, y=10) == "y=10"
        assert sw()(x=1, y=3) == "default"
        assert sw()(x=1) == "default"


class TestCombinedRules:
    """Test combining type and value rules."""

    def test_type_and_value_combined(self):
        """Test combining type and value rules."""
        sw = Switcher()

        @sw(typerule={'x': int}, valrule=lambda x: x > 0)
        def handle_positive_int(x):
            return "positive int"

        @sw(typerule={'x': int}, valrule=lambda x: x < 0)
        def handle_negative_int(x):
            return "negative int"

        @sw(typerule={'x': str})
        def handle_string(x):
            return "string"

        @sw
        def handle_default(x):
            return "default"

        assert sw()(x=5) == "positive int"
        assert sw()(x=-5) == "negative int"
        assert sw()(x="hi") == "string"
        assert sw()(x=0) == "default"

    def test_rule_priority_by_registration_order(self):
        """Test that rules match in registration order."""
        sw = Switcher()

        # Register more specific rule first
        @sw(typerule={'x': int}, valrule=lambda x: x < 0)
        def handle_negative(x):
            return "negative"

        # Register less specific rule second
        @sw(typerule={'x': int})
        def handle_any_int(x):
            return "any int"

        # Default last
        @sw
        def handle_default(x):
            return "default"

        # More specific rule should match first
        assert sw()(x=-5) == "negative"
        # Less specific rule matches positive
        assert sw()(x=5) == "any int"
        # Default matches non-int
        assert sw()(x="text") == "default"


class TestNamedHandlerLookup:
    """Test retrieving handlers by name."""

    def test_get_handler_by_name(self):
        """Test sw('name') retrieves handler by name."""
        sw = Switcher()

        @sw(typerule={'x': int})
        def compute(x):
            return x * 2

        handler = sw('compute')
        assert handler(x=5) == 10

    def test_get_handler_by_name_one_liner(self):
        """Test sw('name')(args) in one line."""
        sw = Switcher()

        @sw(typerule={'x': int})
        def compute(x):
            return x * 2

        assert sw('compute')(x=5) == 10

    def test_handler_not_found_by_name(self):
        """Test that unknown name returns decorator for alias registration."""
        sw = Switcher()

        @sw
        def existing(x):
            return x

        # Getting unknown name returns a decorator (for alias support)
        result = sw('nonexistent')
        assert callable(result)  # It's a decorator

        # Can use it to register with that alias
        @result
        def new_handler(x):
            return "new"

        # Now it's registered and accessible
        assert sw('nonexistent')(x=1) == "new"


class TestCustomAlias:
    """Test custom alias registration with @sw('alias')."""

    def test_register_with_alias(self):
        """Test registering handler with custom alias."""
        sw = Switcher()

        @sw('reset')
        def destroyall():
            return "destroyed"

        # Can call with alias
        assert sw('reset')() == "destroyed"

    def test_alias_different_from_function_name(self):
        """Test alias is different from function name."""
        sw = Switcher()

        @sw('custom_name')
        def my_function():
            return "custom"

        # Accessible by alias
        assert sw('custom_name')() == "custom"

    def test_multiple_aliases(self):
        """Test registering multiple handlers with different aliases."""
        sw = Switcher()

        @sw('action1')
        def handler1():
            return "one"

        @sw('action2')
        def handler2():
            return "two"

        assert sw('action1')() == "one"
        assert sw('action2')() == "two"

    def test_alias_already_registered_raises_error(self):
        """Test that registering with existing alias raises ValueError."""
        sw = Switcher()

        @sw('action')
        def first():
            return "first"

        # Try to register another handler with same alias
        with pytest.raises(ValueError, match="Alias 'action' is already registered"):
            @sw('action')
            def second():
                return "second"

    def test_function_name_already_registered_raises_error(self):
        """Test that registering function with existing name raises ValueError."""
        sw = Switcher()

        @sw
        def my_function():
            return "first"

        # Try to register another function with same name
        with pytest.raises(ValueError, match="Handler 'my_function' already taken by function"):
            @sw
            def my_function():
                return "second"


class TestAutomaticDispatch:
    """Test automatic handler dispatch."""

    def test_automatic_dispatch_with_rules(self):
        """Test sw() automatic dispatch based on rules."""
        sw = Switcher()

        @sw(typerule={'x': int})
        def handle(x):
            return "int"

        @sw(typerule={'x': str})
        def handle(x):
            return "str"

        dispatcher = sw()
        assert dispatcher(x=42) == "int"
        assert dispatcher(x="hi") == "str"

    def test_no_match_raises_error(self):
        """Test ValueError when no rule matches and no default."""
        sw = Switcher()

        @sw(typerule={'x': int})
        def handle(x):
            return "int"

        with pytest.raises(ValueError, match="No rule matched"):
            sw()(x="not an int")

    def test_default_handler_catches_all(self):
        """Test default handler catches unmatched calls."""
        sw = Switcher()

        @sw(typerule={'x': int})
        def handle_int(x):
            return "int"

        @sw
        def handle_default(x):
            return "default"

        # Default catches non-int
        assert sw()(x="text") == "default"
        assert sw()(x=[1,2]) == "default"
        # Specific rule still matches
        assert sw()(x=42) == "int"


class TestPositionalArguments:
    """Test handling of positional arguments."""

    def test_positional_args_mapped_to_params(self):
        """Test positional arguments are mapped to parameter names."""
        sw = Switcher()

        @sw(typerule={'a': int, 'b': int})
        def add(a, b):
            return a + b

        # Positional arguments
        assert sw()(5, 10) == 15

    def test_mixed_positional_and_keyword(self):
        """Test mixing positional and keyword arguments."""
        sw = Switcher()

        @sw(typerule={'x': int, 'y': int})
        def calculate(x, y):
            return x + y

        # Mixed
        assert sw()(5, y=10) == 15
        # All positional
        assert sw()(5, 10) == 15
        # All keyword
        assert sw()(x=5, y=10) == 15


class TestDescriptorProtocol:
    """Test descriptor protocol for class-based usage."""

    def test_descriptor_returns_self_from_class(self):
        """Test accessing Switcher from class returns self."""
        sw = Switcher()

        class MyClass:
            dispatch = sw

        # Accessing from class
        assert MyClass.dispatch is sw

    def test_descriptor_returns_bound_switcher_from_instance(self):
        """Test accessing Switcher from instance returns BoundSwitcher."""
        sw = Switcher()

        @sw
        def method(self, x):
            return f"{self.value} + {x}"

        class MyClass:
            dispatch = sw
            def __init__(self):
                self.value = 10

        obj = MyClass()
        # Accessing from instance
        bound = obj.dispatch
        # Should be BoundSwitcher
        assert bound.__class__.__name__ == 'BoundSwitcher'

    def test_bound_switcher_binds_self(self):
        """Test BoundSwitcher automatically binds self."""
        sw = Switcher()

        @sw
        def method(self, x):
            return f"{self.name}: {x}"

        class MyClass:
            dispatch = sw
            def __init__(self, name):
                self.name = name

        obj = MyClass("test")
        # Get bound version
        bound = obj.dispatch
        # Call handler - self is automatically bound
        handler = bound('method')
        result = handler(x=5)
        assert result == "test: 5"


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_multiple_handlers_with_unique_names(self):
        """Test multiple handlers with unique function names."""
        sw = Switcher()

        @sw(typerule={'x': int})
        def process_int(x):
            return "int"

        @sw(typerule={'x': str})
        def process_str(x):
            return "str"

        @sw
        def process_default(x):
            return "default"

        # All registered with unique names
        assert len(sw._handlers) == 3
        assert len(sw._rules) == 2
        assert sw._default_handler is not None

        # Dispatch works correctly
        assert sw()(x=42) == "int"
        assert sw()(x="hi") == "str"
        assert sw()(x=[1,2]) == "default"

    def test_any_type_always_matches(self):
        """Test that Any type matches everything."""
        sw = Switcher()

        @sw(typerule={'x': Any})
        def handle_any(x):
            return "any"

        assert sw()(x=42) == "any"
        assert sw()(x="text") == "any"
        assert sw()(x=[1,2]) == "any"

    def test_empty_typerule_dict(self):
        """Test handler with empty typerule dict."""
        sw = Switcher()

        @sw(typerule={})
        def handle(x):
            return "empty rule"

        # Should match (no type constraints to fail)
        assert sw()(x=42) == "empty rule"

    def test_valrule_with_missing_param(self):
        """Test valrule doesn't fail on missing params."""
        sw = Switcher()

        # Valrule expects 'y' but we only pass 'x'
        @sw(valrule=lambda **kw: kw.get('y', 0) > 5)
        def handle_matched(x, y=0):
            return "matched"

        @sw
        def handle_default(x, y=0):
            return "default"

        # With y > 5
        assert sw()(x=1, y=10) == "matched"
        # Without y (default 0 <= 5)
        assert sw()(x=1) == "default"

    def test_invalid_call_raises_type_error(self):
        """Test invalid __call__ usage raises TypeError."""
        sw = Switcher()

        # Invalid: passing non-string, non-callable, non-None
        with pytest.raises(TypeError, match="Switcher.__call__ expects"):
            sw(123)


class TestSignatureCaching:
    """Test that signature inspection is cached."""

    def test_signature_cache_populated(self):
        """Test that signature cache is populated on registration."""
        sw = Switcher()

        @sw(typerule={'x': int})
        def handler(x, y):
            return x + y

        # Cache should be populated
        assert handler in sw._param_names_cache
        assert sw._param_names_cache[handler] == ['x', 'y']


class TestRealWorldScenarios:
    """Test realistic usage scenarios."""

    def test_api_router_example(self):
        """Test API request routing scenario."""
        api = Switcher()

        @api(valrule=lambda method, path: method == 'GET' and path == '/users')
        def handle_list_users(method, path):
            return "list users"

        @api(valrule=lambda method, path: method == 'POST' and path == '/users')
        def handle_create_user(method, path):
            return "create user"

        @api
        def handle_not_found(method, path):
            return "not found"

        assert api()(method='GET', path='/users') == "list users"
        assert api()(method='POST', path='/users') == "create user"
        assert api()(method='GET', path='/products') == "not found"

    def test_data_validator_example(self):
        """Test data validation scenario."""
        validator = Switcher()

        @validator(typerule={'value': str},
                   valrule=lambda value: '@' in value)
        def validate_email(value):
            return "email"

        @validator(typerule={'value': int},
                   valrule=lambda value: 0 <= value <= 100)
        def validate_percentage(value):
            return "percentage"

        @validator
        def validate_invalid(value):
            return "invalid"

        assert validator()(value="user@example.com") == "email"
        assert validator()(value=75) == "percentage"
        assert validator()(value="just text") == "invalid"
        assert validator()(value=150) == "invalid"


class TestPrefixBasedAutoNaming:
    """Test prefix-based automatic handler name derivation."""

    def test_prefix_basic_stripping(self):
        """Test basic prefix stripping from function names."""
        sw = Switcher(prefix='handle_')

        @sw
        def handle_foo(x):
            return f"foo: {x}"

        @sw
        def handle_bar(x):
            return f"bar: {x}"

        # Handlers registered with stripped names
        assert 'foo' in sw._handlers
        assert 'bar' in sw._handlers

        # Can access by derived names
        assert sw('foo')(x=5) == "foo: 5"
        assert sw('bar')(x=10) == "bar: 10"

    def test_prefix_no_match_uses_full_name(self):
        """Test function without prefix uses full name."""
        sw = Switcher(prefix='handle_')

        @sw
        def other_name(x):
            return f"other: {x}"

        # Registered with full name (no prefix match)
        assert 'other_name' in sw._handlers
        assert sw('other_name')(x=5) == "other: 5"

    def test_prefix_explicit_name_override(self):
        """Test explicit name overrides prefix stripping."""
        sw = Switcher(prefix='handle_')

        @sw('custom_name')
        def handle_foo(x):
            return x

        # Registered as 'custom_name', not 'foo'
        assert 'custom_name' in sw._handlers
        assert 'foo' not in sw._handlers
        assert sw('custom_name')(x=5) == 5

    def test_prefix_duplicate_detection(self):
        """Test duplicate handler names are detected."""
        sw = Switcher(prefix='protocol_')

        @sw
        def protocol_s3(x):
            return "first"

        # Try to register with explicit name that conflicts
        with pytest.raises(ValueError, match="Alias 's3' is already registered"):
            @sw('s3')
            def other_handler(x):
                return "second"

    def test_no_prefix_backward_compatibility(self):
        """Test backward compatibility when no prefix is set."""
        sw = Switcher()  # No prefix

        @sw
        def my_func(x):
            return x

        # Uses function name as-is
        assert 'my_func' in sw._handlers
        assert sw('my_func')(x=5) == 5

    def test_prefix_with_description(self):
        """Test using prefix together with description."""
        sw = Switcher(
            name='protocol',
            description='Storage protocol dispatcher',
            prefix='protocol_'
        )

        @sw
        def protocol_s3_aws(x):
            return "s3_aws"

        @sw
        def protocol_gcs(x):
            return "gcs"

        assert sw.description == 'Storage protocol dispatcher'
        assert 's3_aws' in sw._handlers
        assert 'gcs' in sw._handlers
        assert sw('s3_aws')(x=1) == "s3_aws"
        assert sw('gcs')(x=1) == "gcs"

    def test_prefix_with_typerule(self):
        """Test prefix works with type rules."""
        sw = Switcher(prefix='cmd_')

        @sw(typerule={'x': int})
        def cmd_add(x):
            return f"add: {x}"

        @sw(typerule={'x': str})
        def cmd_delete(x):
            return f"delete: {x}"

        # Named registration works with rules
        assert 'cmd_add' in sw._handlers
        assert 'cmd_delete' in sw._handlers

        # Can access by name
        assert sw('cmd_add')(x=5) == "add: 5"
        assert sw('cmd_delete')(x="item") == "delete: item"

    def test_prefix_empty_string(self):
        """Test empty string prefix behaves like no prefix."""
        sw = Switcher(prefix='')

        @sw
        def my_handler(x):
            return x

        # Empty prefix = no stripping
        assert 'my_handler' in sw._handlers
        assert sw('my_handler')(x=5) == 5

    def test_prefix_longer_than_name(self):
        """Test prefix longer than function name."""
        sw = Switcher(prefix='very_long_prefix_')

        @sw
        def short(x):
            return x

        # No match, uses full name
        assert 'short' in sw._handlers
        assert sw('short')(x=5) == 5
