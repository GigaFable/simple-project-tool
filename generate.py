import json
import sys
from ruamel.yaml import YAML
from jsonschema import validate, ValidationError
import networkx as nx
import argparse
from rich.console import Console


def parse_yaml(yaml_file):
    yaml = YAML()
    with open(yaml_file) as f:
        data = yaml.load(f)

    with open("schema.json") as f:
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


def topological_sort(*, project):
    G = nx.DiGraph()
    by_title = {}
    sort_stage(
        G=G,
        by_title=by_title,
        parent_stage=None,
        stage=project,
        parallel=False,
    )
    # TODO: Test and handle failure caused by depending on a stage that is not defined
    # TODO: Test and handle cycles in the graph
    # TODO: Check that nothing depends on the project stage itself
    return (
        G,
        by_title,
        list(reversed([by_title[title] for title in nx.topological_sort(G)])),
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


def generate_mermaid_leaf_declaration(*, stage, leaf_ref_generator):
    leaf_ref = leaf_ref_generator.next()
    stage["leaf_ref"] = leaf_ref
    if stage.get("milestone", False):
        return f"    {leaf_ref}{{{{\"{stage['title']}\"}}}}"
    else:
        return f"    {leaf_ref}[\"{stage['title']}\"]"


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

    def generate_mermaid_sub_graphs(self):
        result = f"subgraph {self.stage['title']}\n"
        if self.stage.get("milestone", False):
            result += f"    {self.head_id}{{{{\"{self.stage['title']}\"}}}}\n"
        else:
            result += f"    {self.head_id}[\"{self.stage['title']}\"]\n"

        for sub_graph in self.sub_graphs:
            result += sub_graph.generate_mermaid_sub_graphs()
        for stage in self.sub_stages:
            result += (
                generate_mermaid_leaf_declaration(
                    stage=stage, leaf_ref_generator=self.leaf_ref_generator
                )
                + "\n"
            )
        result += "end\n"
        return result

    def __str__(self):
        return f"SubGraph(title={self.stage}, stages={self.sub_stages})"


def generate_mermaid(*, stages, G, by_title, project, complete_is_tree):
    alpha_label_generator = AlphaLabelGenerator()
    group_id_generator = LeafRefGenerator(prefix="Group_")
    print("flowchart BT")
    project = stages.pop(0)
    project_title = project["title"]
    print(f"    Project{{{{{project["title"]}}}}}")
    print("style Project fill:#4CAF50,stroke:#333,stroke-width:2px,color:#fff")
    flat_sub_graphs = []
    flat_leaves = []
    sub_graph = None
    project_leaf_ref_generator = None

    for stage in stages:
        if complete_is_tree and stage.get("complete", False):
            for requires, required in G.in_edges(stage["title"]):
                requires_stage = by_title[requires]
                requires_stage["complete"] = True

        # Stage parents may not have been created yet so we need to delay
        # both sub graphs and leaves until we have all the sub graphs
        # created.

        # An alternative would be to walk the project tree. This is good enough
        # for now, but may not be the best solution in the future.

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
        for required, requires in G.out_edges(sub_graph.stage["title"]):
            requires_stage = by_title[requires]
            required_stage_ref = sub_graph.head_id
            if requires_stage["title"] == project["title"]:
                print(f"{required_stage_ref} --> Project")
            elif is_leaf(requires_stage):
                print(f'{required_stage_ref} --> {requires_stage["leaf_ref"]}')
            else:
                print(f'{required_stage_ref} --> {requires_stage["sub_graph"].head_id}')

    # Output the edges
    for leaf in flat_leaves:
        required_leaf_ref = leaf["leaf_ref"]
        for required, requires in G.out_edges(leaf["title"]):
            requires_stage = by_title[requires]
            if requires_stage["title"] == project["title"]:
                print(f"{required_leaf_ref} --> Project")
            elif is_leaf(requires_stage):
                print(f'{required_leaf_ref} --> {requires_stage["leaf_ref"]}')
            else:
                print(f'{required_leaf_ref} --> {requires_stage["sub_graph"].head_id}')

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

    args = parser.parse_args()

    project = parse_yaml(args.yaml_file)

    if args.order_of_work:
        console = Console()
        G, by_title, stages = topological_sort(project=project)
        console.print("# Suggested order of work", style="bright_magenta")
        console.print("")
        counter = 1
        for stage in reversed(stages[1:]):  # Exclude the project stage itself
            if is_leaf(stage):
                if stage.get("milestone", False):
                    console.print(
                        f'[bright_cyan]{counter}.[/bright_cyan] {stage["title"]} (milestone)',
                        style="bright_cyan",
                        highlight=False,
                    )
                else:
                    console.print(
                        f'[bright_cyan]{counter}.[/bright_cyan] {stage["title"]}',
                        style="cyan",
                        highlight=False,
                    )
            else:
                if stage.get("milestone", False):
                    console.print(
                        f'[bright_cyan]{counter}.[/bright_cyan] {stage["title"]} (group) (milestone)',
                        style="bright_green",
                        highlight=False,
                    )
                else:
                    console.print(
                        f'[bright_cyan]{counter}.[/bright_cyan] {stage["title"]} (group)',
                        style="green",
                        highlight=False,
                    )
            counter += 1
        console.print(
            f'[bright_cyan]{counter}.[/bright_cyan] {stages[0]["title"]} (project)',
            style="bright_magenta",
            highlight=False,
        )
        console.print(f"\nTotal stages: {counter}", style="bright_yellow")
    else:
        # TODO: This could be replaced by validation as the resulting order of work
        # is only relied upon for obtaining the project stage, which could be
        # easily obtained differently
        G, by_title, stages = topological_sort(project=project)
        generate_mermaid(
            stages=stages,
            G=G,
            by_title=by_title,
            project=project,
            complete_is_tree=args.complete_is_tree,
        )
