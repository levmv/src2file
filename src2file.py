#!/usr/bin/env python3
import os
import sys
import argparse
import fnmatch

MAX_FILE_SIZE = 350 * 1024  # 350KB limit 

DEFAULT_EXTENSIONS = {
    # -- Scripting & Backend (Python, Ruby, PHP, etc) --
    'py', 'pyw', 'pyi', 'rb', 'php', 'pl', 'pm', 'lua', 'ex', 'exs',
    # -- Web & Frontend --
    'js', 'jsx', 'mjs', 'cjs', 'ts', 'tsx', 'vue', 'svelte', 'html', 'css', 'scss', 'less',    
    # -- Systems & Compiled --
    'c', 'h', 'cpp', 'hpp', 'cc', 'cxx', 'cs', 'go', 'mod', 'rs', 'java', 'kt', 'scala', 'swift', 'dart',    
    # -- Shell & Automation --
    'sh', 'bash', 'zsh', 'fish', 'ps1', 'bat', 'makefile', 'cmake',
    # -- Config & Data --
    'json', 'yaml', 'yml', 'toml', 'xml', 'ini', 'sql', 'graphql', 'prisma', 'proto',    
    # -- Docs --
    'md', 'txt', 'rst', 'dockerfile'
}

DEFAULT_IGNORE_PATTERNS = [
    # Any hidden folder (like .git, .vscode) are skipped in code, so they are not specified here
    'node_modules',
    'vendor',
    '__pycache__',
    'venv',
    'dist',
    'build',
    
    'package-lock.json',
    '*.min.js',
    '*.min.css',
]

def sanitize_filename(name):
    return name.replace('-', '_')

def normalize_ext(ext_list):
    return {e.lstrip('.').lower() for e in ext_list}

def load_gitignore(folder_path, root_dir):
    """
    Loads .gitignore from folder_path and rebases rules to be relative to root_dir.
    """
    patterns = []
    gitignore_path = os.path.join(folder_path, '.gitignore')
    
    if not os.path.isfile(gitignore_path):
        return patterns

    try:
        rel_parent = os.path.relpath(folder_path, root_dir).replace(os.sep, '/')
        
        if rel_parent == '.': 
            rel_parent = ''        

        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.split('#')[0].strip()
                if not line: 
                    continue
                
                # We check the "body" of the pattern (ignoring trailing slash).
                # 'src/temp' -> body is 'src/temp' (Has slash -> Anchored)
                # 'dist/' -> body is 'dist' (No slash -> Recursive)
                if '/' in line.rstrip('/'):
                    # Anchored Logic: Preserve structure (keep trailing slash if present)
                    clean_line = line.lstrip('/')
                    if rel_parent:
                        rebased = f"/{rel_parent}/{clean_line}"
                    else:
                        rebased = f"/{clean_line}"
                    patterns.append(rebased)
                else:
                    # Recursive Logic: Strip slash to allow simple name matching
                    patterns.append(line.rstrip('/'))
    except Exception:
        pass
        
    return patterns

def is_ignored(rel_path, ignore_patterns, *, is_dir=False):
    name = os.path.basename(rel_path)
    
    for pattern in ignore_patterns:
        if pattern.endswith('/'):
            norm_pattern = pattern.rstrip('/')
            clean_norm = norm_pattern.lstrip('/')
            
            # Exact Match (e.g. 'node_modules' matches '/src/node_modules/')
            if is_dir and rel_path == clean_norm:
                return True
            # Inside Match (e.g. file inside node_modules)
            if rel_path.startswith(clean_norm + '/'):
                return True
                
        elif pattern.startswith('/'):
            clean_pattern = pattern.lstrip('/')
            if fnmatch.fnmatch(rel_path, clean_pattern):
                return True
                    
        else:
            if fnmatch.fnmatch(name, pattern):
                return True
            # Check full path match for standard patterns
            if fnmatch.fnmatch(rel_path, pattern):
                return True
    return False

def process_file(filepath, rel_path, verbose=False):
    """
    Read file content or return None if binary/unreadable.
    """
    try:
        # Read entire file into memory (needed for context anyway)
        with open(filepath, 'rb') as f:
            content_bytes = f.read()

        # Inline binary check: Look for null byte in first 8KB
        if b'\0' in content_bytes[:8192]:
            if verbose: print(f"Skipping binary file: {rel_path}")
            return None

        return content_bytes.decode('utf-8', errors='replace')
        
    except Exception as e:
        if verbose: print(f"Error reading {rel_path}: {e}")
        return None

def scan_directory(current_dir, root_dir, ignore_context, allowed_extensions, collected, verbose=False):
    """
    Recursively traverse directories and collect files.
    """
    # Combine inherited ignore patterns with local .gitignore rules
    ignore_patterns = ignore_context + load_gitignore(current_dir, root_dir)

    try:
        with os.scandir(current_dir) as entries:
            # Sort for deterministic order
            entries = sorted(list(entries), key=lambda e: e.name)
            
            for entry in entries:
                if entry.name.startswith('.'): continue
                
                if entry.is_symlink():
                    if verbose: print(f"Skipping symlink: {entry.name}")
                    continue

                # Calculate relative path and normalize to /
                rel_path = os.path.relpath(entry.path, root_dir).replace(os.sep, '/')
                
                # --- Directory Handling ---
                if entry.is_dir():
                    if is_ignored(rel_path, ignore_patterns, is_dir=True):
                        continue
                    scan_directory(entry.path, root_dir, ignore_patterns, allowed_extensions, collected, verbose)
                
                # --- File Handling ---
                elif entry.is_file():
                    if is_ignored(rel_path, ignore_patterns, is_dir=False):
                        continue

                    try:
                        if entry.stat().st_size > MAX_FILE_SIZE:
                            if verbose: print(f"Skipping large file ({entry.stat().st_size} bytes): {rel_path}")
                            continue
                    except OSError:
                        continue
                    
                    # Extension Check
                    parts = entry.name.rsplit('.', 1)
                    ext = parts[1].lower() if len(parts) > 1 else ""
                    is_allowed = (entry.name.lower() in allowed_extensions) or (ext in allowed_extensions)
                    
                    if not is_allowed:
                        continue

                    # Process Content
                    content = process_file(entry.path, rel_path, verbose)
                    if content is not None:
                        collected.append((rel_path, content))

    except PermissionError:
        if verbose: print(f"Permission denied: {current_dir}")
    except OSError as e:
        if verbose: print(f"Error scanning {current_dir}: {e}")

def generate_tree(file_paths):
    """Generates a visual directory tree."""
    tree = {}
    for path in file_paths:
        parts = path.split('/')
        current = tree
        for part in parts:
            current = current.setdefault(part, {})

    lines = []
    def _draw(current_level, prefix=""):
        # Sort keys
        keys = sorted(current_level.keys(), key=lambda k: k.lower())
        for i, key in enumerate(keys):
            is_last = (i == len(keys) - 1)
            connector = "└── " if is_last else "├── "
            
            if len(current_level[key]) > 0:
                lines.append(f"{prefix}{connector}{key}/")
                extension = "    " if is_last else "│   "
                _draw(current_level[key], prefix + extension)
            else:
                lines.append(f"{prefix}{connector}{key}")
    _draw(tree)
    return "\n".join(lines)

def collect_files(root_dir, allowed_extensions, base_ignore_patterns, verbose=False):
    collected = []
    
    if verbose:
        print(f"Scanning {root_dir}...")

    scan_directory(
        current_dir=root_dir,
        root_dir=root_dir, 
        ignore_context=base_ignore_patterns, 
        allowed_extensions=allowed_extensions, 
        collected=collected, 
        verbose=verbose
    )
    
    return collected

def save_to_file(files, output_path, root_dir_name):
    if not files:
        print("No files found matching criteria.")
        return

    files.sort(key=lambda x: x[0])
    
    with open(output_path, 'w', encoding='utf-8') as outfile:
        # 1. Write Tree
        outfile.write(f"Project: {root_dir_name}\n")
        outfile.write("=" * 50 + "\n")
        outfile.write("PROJECT STRUCTURE:\n")
        outfile.write(generate_tree([f[0] for f in files]))
        outfile.write("\n" + "=" * 50 + "\n\n")

        # 2. Write Content
        for rel_path, content in files:
            outfile.write(f"FILE: {rel_path}\n")
            outfile.write("-" * 20 + "\n")
            outfile.write(content)
            if not content.endswith('\n'):
                outfile.write('\n')
            outfile.write("\n" + "=" * 50 + "\n\n")

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    # Simple token estimate
    est_tokens = os.path.getsize(output_path) // 4
    print(f"Success! Saved {len(files)} files to {output_path}")
    print(f"Size: {size_mb:.2f} MB | Est. Tokens: ~{est_tokens:,}")

def main():
    parser = argparse.ArgumentParser(description='Flatten source code into a single context file.')
    parser.add_argument('directory', nargs='?', default='.', help='Directory to process')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show processing details')
    
    parser.add_argument('-e', '--extensions', help='Extensions to include (e.g. go,js)')
    parser.add_argument('-s', '--skip', help='Extensions to skip from defaults')
    parser.add_argument('-i', '--ignore', help='Additional ignore patterns')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    
    if not os.path.isdir(args.directory):
        print(f"Error: Directory '{args.directory}' not found.")
        sys.exit(1)

    root_dir = os.path.abspath(args.directory)
    dir_name = sanitize_filename(os.path.basename(root_dir))
    
    ignore_patterns = DEFAULT_IGNORE_PATTERNS.copy()
    if args.ignore:
        ignore_patterns.extend([p.strip() for p in args.ignore.split(',')])

    if args.extensions:
        target_extensions = normalize_ext(args.extensions.split(','))
    else:
        target_extensions = DEFAULT_EXTENSIONS.copy()
    
    if args.skip:
        target_extensions -= normalize_ext(args.skip.split(','))


    files = collect_files(root_dir, target_extensions, ignore_patterns, args.verbose)    
    output_filename = args.output if args.output else f"{dir_name}.txt"

    # Safety check for overwrite
    if os.path.exists(output_filename):
        try:
            with open(output_filename, 'r', encoding='utf-8') as f:
                header = f.read(20)
            
            if not header.startswith("Project:"):
                response = input(f"File '{output_filename}' already exists and doesn't look like a src2file output.\nOverwrite? [y/N]: ")
                if response.lower() != 'y':
                    print("Aborted.")
                    sys.exit(0)
        except Exception:
            response = input(f"File '{output_filename}' already exists.\nOverwrite? [y/N]: ")
            if response.lower() != 'y':
                sys.exit(0)

    save_to_file(files, output_filename, dir_name)

if __name__ == "__main__":
    main()