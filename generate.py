import json
import sys
from ruamel.yaml import YAML
from jsonschema import validate, ValidationError

yaml = YAML()
with open("project.yaml") as f:
    data = yaml.load(f)

with open("schema.json") as f:
    schema = json.load(f)

try:
    validate(instance=data, schema=schema)
    print("YAML is valid according to the schema.")
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
