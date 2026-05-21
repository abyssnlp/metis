# Metis

![metis](/assets/metis.png)

A terminal knowledge base for commands, code snippets, and SQL queries. Organize entries into knowledge bases (e.g. `aws`, `terraform`, `snowflake`), search with keywords or semantic similarity, and copy results straight to your clipboard.

## Features

- Organize snippets into named knowledge bases
- Interactive TUI browser with arrow-key navigation (fzf-style)
- Keyword search and semantic/vector search (ChromaDB)
- Copy to clipboard or print to terminal with a single keypress
- Rich terminal output with colors and tables
- All data stored locally under `~/.metis`

## Installation

```bash
pip install -e .
```

Requires Python 3.9+.

## Quick start

```bash
# Create knowledge bases
metis --kb aws
metis --kb terraform
metis --kb snowflake

# Add entries
metis add --kb aws -t "List VPC subnets" \
  -c "aws ec2 describe-subnets --filters Name=vpc-id,Values=vpc-xxx" \
  -d "Get all subnets in a VPC" --tags "ec2,vpc,networking"

metis add --kb terraform -t "Plan and apply" \
  -c "terraform plan -out=tfplan && terraform apply tfplan" \
  --tags "iac,deploy"

metis add --kb snowflake -t "Get task history" \
  -c "SELECT * FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY()) ORDER BY SCHEDULED_TIME DESC LIMIT 20;" \
  --tags "tasks,monitoring"
```

## Usage

```
metis [OPTIONS] COMMAND [ARGS]
```

### Global options

| Option | Description |
|--------|-------------|
| `metis -V` | Show version |
| `metis -l` / `metis --list` | List all knowledge bases |
| `metis --kb <name>` | Create a new knowledge base |

### Commands

| Command | Description |
|---------|-------------|
| `metis add` | Add an entry (prompts for title and command) |
| `metis find [query]` | Search entries; no query opens interactive browser |
| `metis find -s <query>` | Semantic / vector search |
| `metis find -p <query>` | Search then pick an entry to copy or print |
| `metis ls` | List all entries |
| `metis ls --kb aws` | List entries in a specific knowledge base |
| `metis ls -p` | List then pick an entry to copy or print |
| `metis rm <id>` | Delete an entry by ID |
| `metis reindex` | Rebuild the vector search index |

### Interactive browser (`metis find`)

Running `metis find` with no arguments opens a full-screen TUI:

1. **Knowledge base selector** — pick a KB or "all"
2. **Entry browser** — type to filter, arrows to navigate, `c` to copy, `p` to print

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate entries |
| `→` / `Enter` | Open knowledge base |
| `←` / `Backspace` | Go back to KB list |
| `Ctrl+K` | Toggle search mode (type to filter) |
| `Esc` / `Enter` | Exit search mode |
| `c` | Copy highlighted command to clipboard |
| `p` | Print highlighted command and exit |
| `q` / `Ctrl-C` | Quit |

Type any characters to filter entries by keyword.

## Data storage

All data lives in `~/.metis/`:

```
~/.metis/
├── metis.json        # knowledge bases and entries
└── vectorstore/      # ChromaDB vector index
```

## Development

```bash
# Install in editable mode
pip install -e .

# Lint
pip install ruff
ruff check src/
ruff format src/
```

## License

MIT
