from io import StringIO
import json
import shutil
import sys
from ruamel.yaml import YAML
from jsonschema import validate, ValidationError
from pathlib import Path

from .sort_utilities import topological_sort


def parse_yaml(yaml_file):
    yaml = YAML()
    with open(yaml_file) as f:
        data = yaml.load(f)

    with open(Path(__file__).parent / "schema.json") as f:
        schema = json.load(f)

    try:
        validate(instance=data, schema=schema)
        return data
    except ValidationError as e:
        print("YAML validation error:", e, file=sys.stderr)
        obj = data
        last_obj_with_lc = None
        for key in e.path:
            try:
                obj = obj[key]
                if hasattr(obj, "lc"):
                    last_obj_with_lc = obj
            except Exception:
                obj = None
                break
        # Prefer the most specific object with line info
        if hasattr(obj, "lc"):
            print(f"\nError near line: {obj.lc.line + 1}", file=sys.stderr)
        elif last_obj_with_lc is not None:
            print(f"\nError near line: {last_obj_with_lc.lc.line + 1}", file=sys.stderr)
        else:
            print("\nError location could not be determined.", file=sys.stderr)
        sys.exit(1)


def update_yaml(*, project, complete_is_tree):
    G, by_title, stages = topological_sort(
        project=project, complete_is_tree=complete_is_tree, updating_yaml=True
    )
    # Remove patched keys from stages
    patched_keys = ["parent", "parallel"]
    for stage in stages:
        for key in patched_keys:
            if key in stage:
                del stage[key]

    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=0)
    stream = StringIO()
    yaml.dump(project, stream)
    yaml_string = stream.getvalue()
    prettier_path = shutil.which("prettier")
    if prettier_path:
        # Use prettier to format the YAML
        import subprocess

        result = subprocess.run(
            [prettier_path, "--parser", "yaml"],
            input=yaml_string.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        if result.returncode != 0:
            print(
                "Error formatting YAML with prettier:\n",
                result.stderr.decode(),
                file=sys.stderr,
            )
            sys.exit(2)

        yaml_string = result.stdout.decode()

    print(yaml_string)
