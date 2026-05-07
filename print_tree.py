import os

def print_tree(startpath, prefix=""):
    # skip hidden files/folders
    entries = sorted([e for e in os.listdir(startpath) if not e.startswith(".")])
    for i, name in enumerate(entries):
        path = os.path.join(startpath, name)
        connector = "└── " if i == len(entries) - 1 else "├── "
        print(prefix + connector + name)
        if os.path.isdir(path):
            extension = "    " if i == len(entries) - 1 else "│   "
            print_tree(path, prefix + extension)

# Run from current working directory
print_tree(".")
