from general_utilities import (
    is_leaf,
    AlphaLabelGenerator,
    NodeRefGenerator,
    INDENT_SPACES,
)
from sort_utilities import topological_sort


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


def generate_mermaid(*, project, complete_is_tree):

    # TODO: This could be replaced by validation as the resulting order of work
    # is only relied upon for obtaining the project stage, which could be
    # easily obtained differently. If we do get rid of it, copy out the
    # complete_is_tree logic.
    G, by_title, stages = topological_sort(
        project=project, complete_is_tree=complete_is_tree
    )

    alpha_label_generator = AlphaLabelGenerator()
    group_id_generator = NodeRefGenerator(prefix="Group_")
    print("flowchart BT")
    project_title = project["title"]
    #  A
    print(f'Project(["{project["title"]}"])')
    print("")
    print("style Project fill:#AC36BC,stroke:#333,stroke-width:2px,color:#fff")
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
                project_leaf_ref_generator = NodeRefGenerator(
                    prefix=alpha_label_generator.next()
                )
            stage["leaf_ref"] = project_leaf_ref_generator.next()
            flat_leaves.append(stage)
        else:
            # Sub graph
            sub_graph = SubGraph(
                stage=stage,
                leaf_ref_generator=NodeRefGenerator(alpha_label_generator.next()),
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
            node_id = (
                stage["leaf_ref"] if is_leaf(stage) else stage["sub_graph"].head_id
            )
            if stage.get("milestone", False):
                print(
                    f"style {node_id} fill:#7444EE,stroke:#333,stroke-width:2px,color:#fff"
                )
            else:
                print(
                    f"style {node_id} fill:{"#047D08" if is_leaf(stage) else "#327E96"},stroke:#333,stroke-width:2px,color:#fff"
                )
