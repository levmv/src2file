# src2file

`src2file` is a lightweight CLI tool designed to prepare your source code for Large Language Models (LLMs) like ChatGPT, Claude, DeepSeek, or Llama. 

It recursively scans a directory for source code files, respects `.gitignore`, and formats everything into a clear, prompt-friendly text file.
## Usage

#### Basic Usage
Scans the current directory using smart defaults (includes common code files, ignores .git, node_modules, etc).
```bash
src2file ./my-project
# Creates: my_project.txt
```

#### Specific Extensions
Only include Go and Markdown files (overwrites default list).
```bash
src2file ./my-project -e go,md
```

#### Skip Extensions
Use defaults, but explicitly remove JSON and YAML files.
```bash
src2file ./my-project -s json,yaml
```

#### Ignore Specific Paths
Ignore a specific tests folder or config files (supports glob patterns).
```bash
src2file ./my-project -i "tests/*,config.local.js"
```

### Options

| Flag | Description |
|------|-------------|
| `-o`, `--output` | Specify output filename (default: `{dirname}.txt`). |
| `-v`, `--verbose` | Print every file being added to the list. |
| `-e`, `--extensions` | Comma-separated list of extensions to include. Overwrites defaults. |
| `-s`, `--skip` | Comma-separated list of extensions to exclude from the list. |
| `-i`, `--ignore` | Additional glob patterns to ignore (e.g. `tests/*`). |



## Installation

```bash
pip install git+https://github.com/levmv/src2file.git