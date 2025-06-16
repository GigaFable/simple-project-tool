import json
import sys
from ruamel.yaml import YAML
from jsonschema import validate, ValidationError
import networkx as nx


def parse_yaml(yaml_file):
    yaml = YAML()
    with open(yaml_file) as f:
        data = yaml.load(f)

    with open("schema.json") as f:
        schema = json.load(f)

    try:
        validate(instance=data, schema=schema)
        print("YAML is valid according to the schema.")
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


def sort_stage(*, G, by_title, parent_stage, stage, parallel):
    by_title[stage["title"]] = stage
    G.add_node(stage["title"])
    if "depends_on" in stage:
        for dependency in stage["depends_on"]:
            G.add_edge(dependency, stage["title"])

    if "stages" in stage:
        previous_stage = None
        for sub_stage in stage["stages"]:
            sort_stage(
                G=G,
                by_title=by_title,
                parent_stage=stage,
                stage=sub_stage,
                parallel=False,
            )
            if previous_stage is not None:
                G.add_edge(previous_stage["title"], sub_stage["title"])
            previous_stage = sub_stage
        if previous_stage is not None and parent_stage is not None:
            G.add_edge(previous_stage["title"], stage["title"])
    if "parallel_stages" in stage:
        for sub_stage in stage["parallel_stages"]:
            sort_stage(
                G=G,
                by_title=by_title,
                parent_stage=stage,
                stage=sub_stage,
                parallel=True,
            )
    if parallel:
        if parent_stage is None:
            raise ValueError("Parallel stages must have a parent stage to connect to.")
        G.add_edge(stage["title"], parent_stage["title"])
        stage["parallel"] = True


def topological_sort(*, data):
    G = nx.DiGraph()
    by_title = {}
    sort_stage(
        G=G,
        by_title=by_title,
        parent_stage=None,
        stage=data,
        parallel=False,
    )
    return list(nx.topological_sort(G))


if __name__ == "__main__":
    data = parse_yaml(sys.argv[1] if len(sys.argv) > 1 else "project.yaml")
    stage_titles = topological_sort(data=data)
    for title in stage_titles:
        print(title)
