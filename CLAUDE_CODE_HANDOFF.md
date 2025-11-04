# SmartSwitch - Handoff to Claude Code

## 📋 Contesto del Progetto

**SmartSwitch** è una libreria Python per dispatch intelligente di funzioni basato su regole di tipo e valore.

### Stato Attuale
✅ **Codice completo e testato**
- Classe `Switcher` ottimizzata e funzionante
- 22 test completi con 95% coverage
- Bug trovati e corretti (registrazione nome handler)
- Refactoring da `SwitchBook` → `Switcher` completato

✅ **CI/CD Setup Completo**
- GitHub Actions workflows (test, docs, publish)
- Codecov configurato (target 90%)
- Read the Docs configurato
- pyproject.toml con dipendenze dev/docs/all

✅ **Documentazione Strutturata**
- MkDocs con Material theme
- Homepage, Installation, Quick Start completi
- Guida Basic Usage completa
- Placeholder per guide avanzate ed esempi

## 🎯 Cosa Deve Fare Claude Code

### 1. Inizializzazione Git e Push su GitHub

```bash
cd /Users/gporcari/Sviluppo/genro_ng/smartswitch

# Inizializza repository
git init
git add .
git commit -m "Initial commit: SmartSwitch v0.1.0

- Core Switcher class with type and value rule dispatch
- 22 comprehensive tests with 95% coverage
- Complete CI/CD setup (GitHub Actions, Codecov, ReadTheDocs)
- Full documentation structure with MkDocs
- Optimized implementation with caching and pre-compiled type checks"

# Crea e collega repository GitHub
git branch -M main
git remote add origin https://github.com/softwell-it/smartswitch.git
git push -u origin main
```

### 2. Creazione Repository GitHub

**Dettagli repository:**
- **Owner:** softwell-it
- **Nome:** smartswitch
- **Descrizione:** Intelligent rule-based function dispatch for Python
- **Visibilità:** Public
- **Topics:** `python`, `dispatch`, `rule-engine`, `type-system`, `functional-programming`
- **README:** Già presente
- **License:** MIT (già presente come LICENSE file)

### 3. Configurazione GitHub Settings

**Branch Protection (main):**
- ✅ Require pull request reviews before merging
- ✅ Require status checks to pass (Tests, Lint)
- ✅ Require branches to be up to date before merging

**GitHub Actions Secrets:**
- `CODECOV_TOKEN` - Da ottenere da codecov.io dopo aver collegato il repository

### 4. Setup Servizi Esterni

**Codecov.io:**
1. Vai su https://codecov.io
2. Collega account GitHub se non già fatto
3. Aggiungi repository `softwell-it/smartswitch`
4. Copia il token e aggiungilo come secret `CODECOV_TOKEN` su GitHub

**Read the Docs:**
1. Vai su https://readthedocs.org
2. Importa progetto da GitHub
3. Repository: `softwell-it/smartswitch`
4. Il file `.readthedocs.yaml` è già configurato

## 📁 Struttura Progetto

```
smartswitch/
├── .github/workflows/        # CI/CD pipelines
│   ├── test.yml             # Multi-OS tests + coverage
│   ├── docs.yml             # Documentation build
│   └── publish.yml          # PyPI release automation
├── .codecov.yml             # Coverage target: 90%
├── .readthedocs.yaml        # RTD configuration
├── .gitignore               # Git ignore patterns
├── mkdocs.yml               # Documentation config
├── pyproject.toml           # Package config + tools
├── README.md                # Project overview
├── docs/                    # Documentation source
│   ├── index.md            # ✅ Complete
│   ├── installation.md     # ✅ Complete
│   ├── quickstart.md       # ✅ Complete
│   └── guide/basic.md      # ✅ Complete
├── src/smartswitch/
│   ├── __init__.py         # Exports Switcher
│   └── core.py             # Main Switcher class
└── tests/
    ├── test_smartswitch.py      # Basic test
    └── test_complete.py         # 22 comprehensive tests
```

## 🧪 Test Rapidi

### Verificare che tutto funzioni:

```bash
# Test
pytest tests/ -v --cov=smartswitch

# Lint
ruff check src/smartswitch/
black --check src/smartswitch/

# Build docs
mkdocs build

# Test import
python3 -c "from smartswitch import Switcher; print('OK')"
```

**Risultati attesi:**
- ✅ 22/22 tests passed
- ✅ 95% coverage
- ✅ No lint errors
- ✅ Docs build successfully
- ✅ Import works

## 📝 Informazioni Tecniche Importanti

### Bug Corretti Durante Sviluppo
1. **Handler non registrati per nome**: Le funzioni con regole (`typerule`/`valrule`) non venivano aggiunte a `_spells`, quindi non recuperabili per nome. 
   - **Fix**: Aggiunta riga `self._spells[func.__name__] = func` nel decorator.

### Ottimizzazioni Implementate
- Signature caching (inspect.signature chiamato una sola volta)
- Type checks pre-compilati
- Manual kwargs building (no bind_partial)
- __slots__ per ridurre memoria

### Test Coverage
- Coverage attuale: **95%** (73/77 lines)
- Mancano solo 4 linee (gestione tipo `Any`, raramente usato)

## 🚀 Prossimi Task (Opzionali)

Dopo il setup iniziale, potrebbero essere utili:

### Documentazione da Completare
- [ ] `docs/guide/typerules.md` - Deep dive type rules
- [ ] `docs/guide/valrules.md` - Deep dive value rules  
- [ ] `docs/guide/named-handlers.md` - Registry pattern
- [ ] `docs/guide/best-practices.md` - Best practices
- [ ] `docs/examples/*.md` - Real world examples
- [ ] `docs/api/switcher.md` - API reference con mkdocstrings

### Release Checklist
- [ ] Verify all tests pass on CI
- [ ] Check documentation builds on RTD
- [ ] Update version in `pyproject.toml` and `__init__.py`
- [ ] Create git tag: `git tag -a v0.1.0 -m "Release 0.1.0"`
- [ ] Push tag: `git push origin v0.1.0`
- [ ] GitHub Actions will automatically publish to PyPI

## 🔗 Link Utili

- **Repository:** https://github.com/softwell-it/smartswitch (da creare)
- **Documentation:** https://smartswitch.readthedocs.io (dopo setup RTD)
- **PyPI:** https://pypi.org/project/smartswitch/ (dopo first release)
- **Codecov:** https://codecov.io/gh/softwell-it/smartswitch (dopo setup)

## 💡 Note per Claude Code

- Il progetto è **100% pronto per il push**
- Tutti i file sono coerenti (Switcher invece di SwitchBook)
- La struttura CI/CD segue le best practices di gtext
- Non ci sono dipendenze esterne nel codice core (solo stdlib)
- pyproject.toml configurato per Python 3.10+

## 🎯 Obiettivo Finale

Avere smartswitch su GitHub con:
1. ✅ Repository pubblico
2. ✅ CI/CD funzionante (tests, lint, docs)
3. ✅ Codecov integration
4. ✅ ReadTheDocs live
5. 📦 Pronto per release su PyPI (quando necessario)

---

**Creato da:** Claude (Anthropic)  
**Data:** 2025-11-04  
**Versione Progetto:** 0.1.0 (pre-release)
