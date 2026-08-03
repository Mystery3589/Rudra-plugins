# rudra-plugins

Official plugin repository for [rudra](https://github.com/Mystery3589/rudra).

Each subdirectory here is a self-contained plugin named `rudra-<name>/`.
Install any plugin with one command:

```bash
rudra plugin install <name>
```

Browse available plugins:

```bash
rudra plugin browse
```

---

## Plugin directory layout

Every plugin must follow this structure:

```
rudra-<name>/
├── plugin.toml          required — manifest
├── README.md            recommended
└── <name>/              Python package (name matches plugin name, hyphens → underscores)
    ├── __init__.py      required — must expose register(app)
    └── commands.py      your @app.command() functions
```

### plugin.toml

```toml
[plugin]
name        = "backup"           # short name — must match directory rudra-backup/
version     = "0.1.0"
description = "Automated backup management with restic and borgbackup"
author      = "Your Name"
rudra_min   = "0.1.0"           # minimum rudra version
homepage    = "https://github.com/you/rudra-backup"
license     = "MIT"

# The subcommand names this plugin registers on rudra's main CLI
commands    = ["backup"]
```

### __init__.py

The only required contract is a `register(app)` function:

```python
import typer
from backup.commands import app as backup_app

def register(app: typer.Typer) -> None:
    app.add_typer(backup_app, name="backup", help="Backup management.")
```

Rudra calls `register(app)` at startup, passing its main Typer app.
Your plugin attaches its subcommands there. That's the entire API.

---

## Scaffold a new plugin

```bash
rudra plugin create myfeature
# creates ./rudra-myfeature/ with the right structure
```

Develop locally, then:

```bash
rudra plugin install ./rudra-myfeature
rudra myfeature --help
```

---

## Submitting to this repo

1. Fork this repo
2. Add your `rudra-<name>/` directory
3. Add your plugin to `plugins.json`:
   ```json
   "myfeature": {
     "version": "0.1.0",
     "description": "One-line description"
   }
   ```
4. Open a pull request

Guidelines:
- Plugin name must be lowercase, hyphens only (no underscores in the directory name)
- Must include a `plugin.toml` and a working `register(app)` function
- Must not shadow any core rudra command name (`system`, `project`, `archive`, `security`, `recon-tools`, `setup`, `plugin`, `version`, `self-upgrade`, `update`, `upgrade`, `full-upgrade`, `install`, `remove`, `search`, `scan`, `recon`, `extract`, `managers`, `service`)
- README.md is required for submission

---

## Plugin loading details (for authors)

- Plugins are loaded from `~/.rudra/plugins/rudra-<name>/`
- The plugin directory is added to `sys.path` before import, so you can use relative imports within your package
- Load failures are isolated: a broken plugin is skipped and its traceback written to `~/.rudra/plugin_errors.log`
- Other plugins and all core rudra commands are never affected by a plugin failure
- `rudra plugin errors` shows the error log
