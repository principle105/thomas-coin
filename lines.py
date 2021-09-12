import pathlib

all_paths = list(pathlib.Path("./src").glob("**/*.py"))
print(sum(sum(1 for _ in open(p, "r")) for p in all_paths))
