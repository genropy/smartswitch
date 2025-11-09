# SmartSwitch Interactive Tutorials

Interactive Jupyter notebooks to learn SmartSwitch step by step.

## 📚 Tutorial Series

Follow these tutorials in order for the best learning experience:

### [01 - Named Handlers](01_named_handlers.ipynb) ⭐ Start here!
**Time**: ~5 minutes | **Level**: Beginner

Learn the basics of SmartSwitch:
- Register functions by name with decorators
- Call handlers dynamically
- Build command dispatchers and CLI tools

**Concepts**: `@switcher`, `switcher('name')(args)`, `entries()`

---

### [02 - Hierarchical Names](02_hierarchical_names.ipynb)
**Time**: ~7 minutes | **Level**: Beginner

Organize handlers for scalable APIs:
- Use prefixes for auto-naming
- Build hierarchical structures
- Navigate with dot notation
- Discover APIs dynamically

**Concepts**: `prefix="user_"`, `mainswitch.add()`, `switcher('users.create')`

---

### [03 - Value-Based Dispatch](03_value_dispatch.ipynb)
**Time**: ~10 minutes | **Level**: Intermediate

Automatic routing based on runtime values:
- Eliminate long if/elif chains
- Declarative routing rules
- Build HTTP routers and state machines
- Handle complex conditions

**Concepts**: `valrule=lambda ...`, `switcher()(args)`, first-match-wins

---

### [04 - Type-Based Dispatch](04_type_dispatch.ipynb)
**Time**: ~10 minutes | **Level**: Intermediate

Automatic routing based on argument types:
- Process different types differently
- Multi-parameter type checking
- Union types and custom classes
- Combine type and value rules

**Concepts**: `typerule={'param': Type}`, `int | float`, type + value rules

---

## 🚀 Quick Start

### Option 1: Run Locally

```bash
# Install SmartSwitch
pip install smartswitch

# Install Jupyter
pip install jupyter

# Start Jupyter
cd notebooks
jupyter notebook
```

### Option 2: Run on Google Colab

Click the "Open in Colab" badge in each notebook.

### Option 3: Run on Binder

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/genropy/smartswitch/main?filepath=notebooks)

---

## 📖 Companion Documentation

Each tutorial corresponds to a documentation guide:

| Tutorial | Documentation |
|----------|---------------|
| 01 - Named Handlers | [Named Handlers Guide](https://smartswitch.readthedocs.io/guide/named-handlers/) |
| 02 - Hierarchical Names | [API Discovery Guide](https://smartswitch.readthedocs.io/guide/api-discovery/) |
| 03 - Value Dispatch | [Value Rules Guide](https://smartswitch.readthedocs.io/guide/valrules/) |
| 04 - Type Dispatch | [Type Rules Guide](https://smartswitch.readthedocs.io/guide/typerules/) |

---

## 🎯 Learning Path

```
01: Named Handlers (5 min)
    ↓
    Learn: @switcher, call by name
    ↓
02: Hierarchical Names (7 min)
    ↓
    Learn: prefix, dot notation, discovery
    ↓
03: Value Dispatch (10 min)
    ↓
    Learn: valrule, automatic routing
    ↓
04: Type Dispatch (10 min)
    ↓
    Learn: typerule, type-based routing
    ↓
🎉 You're ready for production!
```

**Total time**: ~30 minutes for complete mastery

---

## 💡 Tips

- **Run the code!** Each notebook has executable examples
- **Do the exercises** - They reinforce learning
- **Experiment** - Modify examples to see what happens
- **Check the docs** - Links at the end of each tutorial

---

## 🆘 Getting Help

- **Questions?** Open an [issue](https://github.com/genropy/smartswitch/issues)
- **Bugs in notebooks?** Also [issue](https://github.com/genropy/smartswitch/issues)
- **Documentation**: [smartswitch.readthedocs.io](https://smartswitch.readthedocs.io/)

---

## 📝 License

These notebooks are part of SmartSwitch and licensed under MIT.

Feel free to use them for learning, teaching, or workshops!
