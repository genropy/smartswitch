# Changelog

All notable changes to SmartSwitch will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2025-11-11

### Added

- **Plugin System**: Complete plugin architecture for extensible functionality
  - New `.plug()` method to register plugins (standard or external)
  - Standard plugins loaded by string name: `sw.plug('logging', mode='silent')`
  - External plugins imported and instantiated: `sw.plug(YourPlugin())`
  - Plugin access via attribute syntax: `sw.logger.history()`
  - Custom plugin naming support: `sw.plug(plugin, name='custom')`
  - Plugin chaining: Multiple plugins work together seamlessly
  - `SwitcherPlugin` protocol defined in `src/smartswitch/plugin.py`

- **LoggingPlugin Improvements**: Refactored as first standard plugin
  - Cleaner API with simplified method names:
    - `sw.logger.history()` (was: `get_log_history()`)
    - `sw.logger.clear()` (was: `clear_log_history()`)
    - `sw.logger.export()` (was: `export_log_history()`)
    - `sw.logger.set_file()` (was: `configure_log_file()`)
    - `sw.logger.set_mode()` (was: `set_log_mode()`)
  - Accessible via `sw.logger` after `sw.plug('logging')`
  - All functionality preserved with cleaner interface

- **Documentation**: Comprehensive plugin development guide
  - `docs/plugin-development.md`: Complete guide for external developers
  - Protocol explanation with examples
  - Basic and advanced plugin examples (CallCounterPlugin, AsyncPlugin)
  - Best practices and FAQ
  - Section for creating external plugin packages
  - README updated with Plugin System section

### Changed

- **Core Architecture**: Added plugin infrastructure to `Switcher` class
  - New `_plugins` list and `_plugin_registry` dict in `__slots__`
  - `__getattr__` implementation for plugin attribute access
  - `_get_standard_plugin()` method for built-in plugins
  - Decorator now applies plugins during handler registration

### Technical Details

- 35 comprehensive tests for plugin system
- 93% test coverage on LoggingPlugin
- ~1500 lines of code added
- Zero breaking changes to existing API
- Type-safe plugin protocol

## [0.4.0] - 2025-11-05

### Added

- **Logging System**: Call history tracking with multiple modes
  - Silent mode: Zero-overhead history tracking (default)
  - Log mode: Print to console with optional timing
  - Real-time file logging to JSONL format
  - Performance analysis: Find slowest/fastest calls
  - Error tracking: Filter failed executions
  - History queries: By handler, time range, count
  - Export capabilities: JSON file export

### Documentation

- Complete logging guide at `docs/guide/logging.md`
- Examples for all logging modes and queries
- Performance analysis patterns

## [0.3.1] - 2025-10-28

### Added

- **Hierarchical Switchers**: Organize multiple Switchers
  - `.add()` method to create parent-child relationships
  - Dot notation access: `mainswitch('users.list')`
  - Iterate children via `.children` property
  - Useful for organizing large APIs

## [0.3.0] - 2025-10-20

### Added

- **API Discovery**: Handler introspection
  - `.entries()` method lists all registered handler names
  - Enables runtime API exploration
  - Useful for debugging and documentation

## [0.2.0] - 2025-10-10

### Added

- **Prefix-based auto-naming**: Convention-driven handler registration
  - Set `prefix` parameter on Switcher
  - Automatically derives handler names from function names
  - Example: `protocol_s3_aws` → `s3_aws`

### Fixed

- Handler name registration when using typerule/valrule decorators

## [0.1.0] - 2025-09-15

### Added

- Initial release
- **Type-based dispatch**: Route by argument types
- **Value-based dispatch**: Match on runtime values with lambda rules
- **Combined rules**: Use type AND value rules together
- **Named handler access**: Retrieve handlers by name
- **Custom aliases**: Register handlers with user-friendly names
- Clean decorator API with zero dependencies
- Comprehensive test suite (22 tests, 95% coverage)
- Complete documentation with examples

[0.5.0]: https://github.com/genropy/smartswitch/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/genropy/smartswitch/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/genropy/smartswitch/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/genropy/smartswitch/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/genropy/smartswitch/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/genropy/smartswitch/releases/tag/v0.1.0
