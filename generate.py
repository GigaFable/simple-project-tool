from io import StringIO
import json
import shutil
import sys
from ruamel.yaml import YAML
from jsonschema import validate, ValidationError
import networkx as nx
import argparse
from rich.console import Console
from pathlib import Path

INDENT_SPACES = 4


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


def sort_stage(*, G, by_title, parent_stage, stage, parallel):
    by_title[stage["title"]] = stage
    stage["parent"] = parent_stage
    G.add_node(stage["title"])

    if "depends_on" in stage:
        for dependency in stage["depends_on"]:
            G.add_edge(dependency, stage["title"])

    if "stages" in stage:
        previous_sub_stage = None
        for sub_stage in stage["stages"]:
            sort_stage(
                G=G,
                by_title=by_title,
                parent_stage=stage,
                stage=sub_stage,
                parallel=False,
            )
            if previous_sub_stage is not None:
                G.add_edge(previous_sub_stage["title"], sub_stage["title"])
            previous_sub_stage = sub_stage
        if previous_sub_stage is not None:
            G.add_edge(previous_sub_stage["title"], stage["title"])

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


def topological_sort(*, project, complete_is_tree):
    G = nx.DiGraph()
    by_title = {}
    sort_stage(
        G=G,
        by_title=by_title,
        parent_stage=None,
        stage=project,
        parallel=False,
    )

    stages = list([by_title[title] for title in nx.topological_sort(G)])
    for stage in stages:
        if complete_is_tree and stage.get("complete", False):
            for from_node, to_node in G.out_edges(stage["title"]):
                to_node_stage = by_title[to_node]
                to_node_stage["complete"] = True

    # TODO: Test and handle failure caused by depending on a stage that is not defined
    # TODO: Test and handle cycles in the graph
    # TODO: Check that nothing depends on the project stage itself
    return (
        G,
        by_title,
        stages,
    )


def is_leaf(stage):
    return not ("parallel_stages" in stage or "stages" in stage)


class AlphaLabelGenerator:
    def __init__(self):
        self.n = 1

    def next(self):
        label = self._number_to_label(self.n)
        self.n += 1
        return label

    @staticmethod
    def _number_to_label(n):
        result = ""
        while n > 0:
            n, rem = divmod(n - 1, 26)
            result = chr(rem + ord("A")) + result
        return result


class LeafRefGenerator:
    def __init__(self, prefix):
        self.n = 1
        self.prefix = prefix

    def next(self):
        label = f"{self.prefix}{self.n}"
        self.n += 1
        return label


def generate_mermaid_leaf_declaration(
    *, stage, leaf_ref_generator, indentation_level=0
):
    indent = " " * (INDENT_SPACES * indentation_level)
    leaf_ref = leaf_ref_generator.next()
    stage["leaf_ref"] = leaf_ref
    if stage.get("milestone", False):
        return f"{indent}{leaf_ref}{{{{\"{stage['title']}\"}}}}"
    else:
        return f"{indent}{leaf_ref}[\"{stage['title']}\"]"


class SubGraph:
    def __init__(self, *, stage, leaf_ref_generator, group_id):
        self.stage = stage
        self.group_id = group_id
        self.head_id = f"{group_id}_head"
        self.sub_stages = []
        self.sub_graphs = []
        self.leaf_ref_generator = leaf_ref_generator

    def add_stage(self, stage):
        self.sub_stages.append(stage)

    def add_sub_graph(self, sub_graph):
        self.sub_graphs.append(sub_graph)

    def generate_mermaid_sub_graphs(self, *, indentation_level=0):
        single_indent = " " * INDENT_SPACES
        indent = " " * (INDENT_SPACES * indentation_level)
        result = f"{indent}subgraph \"{self.stage['title']}\"\n"
        if self.stage.get("milestone", False):
            result += f"{indent}{single_indent}{self.head_id}{{{{\"{self.stage['title']}\"}}}}\n"
        else:
            result += (
                f"{indent}{single_indent}{self.head_id}[\"{self.stage['title']}\"]\n"
            )

        for sub_graph in self.sub_graphs:
            result += sub_graph.generate_mermaid_sub_graphs(
                indentation_level=indentation_level + 1
            )
        for stage in self.sub_stages:
            result += (
                generate_mermaid_leaf_declaration(
                    stage=stage,
                    leaf_ref_generator=self.leaf_ref_generator,
                    indentation_level=indentation_level + 1,
                )
                + "\n"
            )
        result += f"{indent}end\n"
        return result

    def __str__(self):
        return f"SubGraph(title={self.stage}, stages={self.sub_stages})"


def generate_mermaid(*, stages, G, by_title, project):
    alpha_label_generator = AlphaLabelGenerator()
    group_id_generator = LeafRefGenerator(prefix="Group_")
    print("flowchart BT")
    project_title = project["title"]
    print(f"Project{{{{{project["title"]}}}}}")
    print("")
    print("style Project fill:#4CAF50,stroke:#333,stroke-width:2px,color:#fff")
    print("")
    flat_sub_graphs = []
    flat_leaves = []
    sub_graph = None
    project_leaf_ref_generator = None

    # Stage parents may not have been created yet so we need to delay
    # both sub graphs and leaves until we have all the sub graphs
    # created.

    # An alternative would be to walk the project tree. This is good enough
    # for now, but may not be the best solution in the future.
    for stage in stages:
        # YAML validation ensures every stage has a parent
        if is_leaf(stage):
            # Generate leaf ref here as patching it elsewhere
            # did not work with certain structures.
            if project_leaf_ref_generator is None:
                project_leaf_ref_generator = LeafRefGenerator(
                    prefix=alpha_label_generator.next()
                )
            stage["leaf_ref"] = project_leaf_ref_generator.next()
            flat_leaves.append(stage)
        else:
            # Sub graph
            sub_graph = SubGraph(
                stage=stage,
                leaf_ref_generator=LeafRefGenerator(alpha_label_generator.next()),
                group_id=group_id_generator.next(),
            )

            stage["sub_graph"] = sub_graph

            flat_sub_graphs.append(sub_graph)

    for sub_graph in flat_sub_graphs:
        for inner_sub_graph in flat_sub_graphs:
            if (
                "parent" in inner_sub_graph.stage
                and inner_sub_graph.stage["parent"]
                and sub_graph.stage["title"] == inner_sub_graph.stage["parent"]["title"]
            ):
                sub_graph.add_sub_graph(inner_sub_graph)

    for leaf in flat_leaves:
        if leaf["parent"]["title"] == project_title:
            print(
                generate_mermaid_leaf_declaration(
                    stage=leaf, leaf_ref_generator=project_leaf_ref_generator
                )
            )
        else:
            for sub_graph in flat_sub_graphs:
                if sub_graph.stage["title"] == leaf["parent"]["title"]:
                    sub_graph.add_stage(leaf)
                    break

    for sub_graph in flat_sub_graphs:
        if (
            "parent" in sub_graph.stage
            and sub_graph.stage["parent"]
            and sub_graph.stage["parent"]["title"] == project_title
        ):
            print(sub_graph.generate_mermaid_sub_graphs())

    # Output the edges
    for sub_graph in flat_sub_graphs:
        for from_node, to_node in G.out_edges(sub_graph.stage["title"]):
            to_stage_node = by_title[to_node]
            from_node_ref = sub_graph.head_id
            if to_stage_node["title"] == project["title"]:
                print(f"{from_node_ref} --> Project")
            elif is_leaf(to_stage_node):
                print(f'{from_node_ref} --> {to_stage_node["leaf_ref"]}')
            else:
                print(f'{from_node_ref} --> {to_stage_node["sub_graph"].head_id}')

    # Output the edges
    for leaf in flat_leaves:
        from_leaf_ref = leaf["leaf_ref"]
        for from_node, to_node in G.out_edges(leaf["title"]):
            to_stage_node = by_title[to_node]
            if to_stage_node["title"] == project["title"]:
                print(f"{from_leaf_ref} --> Project")
            elif is_leaf(to_stage_node):
                print(f'{from_leaf_ref} --> {to_stage_node["leaf_ref"]}')
            else:
                print(f'{from_leaf_ref} --> {to_stage_node["sub_graph"].head_id}')

    print("")

    # Show complete stages in green
    for stage in stages:
        if stage.get("complete", False):
            if is_leaf(stage):
                print(
                    f'style {stage["leaf_ref"]} fill:#4CAF50,stroke:#333,stroke-width:2px,color:#fff'
                )
            else:
                print(
                    f'style {stage["sub_graph"].head_id} fill:#4CAF50,stroke:#333,stroke-width:2px,color:#fff'
                )


def order_of_work(*, project, complete_is_tree, incomplete_only):
    console = Console()
    G, by_title, stages = topological_sort(
        project=project, complete_is_tree=complete_is_tree
    )
    console.print("# Suggested order of work", style="bright_magenta")
    console.print("")
    counter = 0
    for stage in stages[:-1]:  # Exclude the project stage itself
        if incomplete_only and stage.get("complete", False):
            continue
        counter += 1
        # TODO: We could use suffix and colour to remove the need for 4 print statements
        suffix = ""
        if stage.get("complete", False):
            suffix = " ✅"
        if is_leaf(stage):
            if stage.get("milestone", False):
                console.print(
                    f'[bright_cyan]{counter}.[/bright_cyan] {stage["title"]} (milestone){suffix}',
                    style="bright_cyan",
                    highlight=False,
                )
            else:
                console.print(
                    f'[bright_cyan]{counter}.[/bright_cyan] {stage["title"]}{suffix}',
                    style="cyan",
                    highlight=False,
                )
        else:
            if stage.get("milestone", False):
                console.print(
                    f'[bright_cyan]{counter}.[/bright_cyan] {stage["title"]} (group) (milestone){suffix}',
                    style="bright_green",
                    highlight=False,
                )
            else:
                console.print(
                    f'[bright_cyan]{counter}.[/bright_cyan] {stage["title"]} (group){suffix}',
                    style="green",
                    highlight=False,
                )
    # Project stage
    if not (incomplete_only and project.get("complete", False)):
        counter += 1
        console.print(
            f'[bright_cyan]{counter}.[/bright_cyan] {project["title"]} (project)',
            style="bright_magenta",
            highlight=False,
        )
    console.print(f"\nTotal stages: {counter}", style="bright_yellow")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple project tool")
    parser.add_argument(
        "yaml_file", nargs="?", default="project.yaml", help="YAML project file"
    )
    parser.add_argument(
        "-o",
        "--order-of-work",
        action="store_true",
        help="Output suggested order of work instead of Mermaid diagram",
    )
    parser.add_argument(
        "-c",
        "--complete-is-tree",
        action="store_true",
        help="Treat all stages required for a stage as completed if a stage is",
    )
    parser.add_argument(
        "-i",
        "--incomplete-only",
        action="store_true",
        help="Only show incomplete stages in the order of work",
    )
    parser.add_argument(
        "-u",
        "--update-yaml",
        action="store_true",
        help="Outputs an up to date YAML file. Use with --complete-is-tree to update the complete status of stages.",
    )

    args = parser.parse_args()

    project = parse_yaml(args.yaml_file)

    if args.order_of_work:
        if args.update_yaml:
            print(
                "The --update-yaml option is not supported with --order-of-work. "
                "Use --complete-is-tree to update the complete status of stages.",
                file=sys.stderr,
            )
            sys.exit(1)
        order_of_work(
            project=project,
            complete_is_tree=args.complete_is_tree,
            incomplete_only=args.incomplete_only,
        )
    elif args.update_yaml:
        if args.incomplete_only:
            print("The --incomplete-only option is not supported for YAML update.")
            sys.exit(1)
        if args.order_of_work:
            print(
                "The --order-of-work option is not supported for YAML update. "
                "Use --complete-is-tree to update the complete status of stages.",
                file=sys.stderr,
            )
            sys.exit(1)
        if not args.complete_is_tree:
            print(
                "The --complete-is-tree option is required for YAML update.",
                file=sys.stderr,
            )
            sys.exit(1)
        G, by_title, stages = topological_sort(
            project=project, complete_is_tree=args.complete_is_tree
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
        if shutil.which("prettier"):
            # Use prettier to format the YAML
            import subprocess

            result = subprocess.run(
                ["prettier", "--parser", "yaml"],
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

    else:
        if args.incomplete_only:
            print("The --incomplete-only option is not supported for Mermaid output.")
            sys.exit(1)
        # TODO: This could be replaced by validation as the resulting order of work
        # is only relied upon for obtaining the project stage, which could be
        # easily obtained differently. If we do get rid of it, copy out the
        # complete_is_tree logic.
        G, by_title, stages = topological_sort(
            project=project, complete_is_tree=args.complete_is_tree
        )
        generate_mermaid(stages=stages, G=G, by_title=by_title, project=project)
