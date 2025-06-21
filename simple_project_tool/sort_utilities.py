import sys
import networkx as nx
from .general_utilities import is_leaf


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


# We always walk the tree to sort out priorities. We also take care of
# complete_is_tree here.
def walk_the_tree(*, G, by_title, stage, complete_is_tree, updating_yaml):
    """Walks the tree to set the `complete` flag for each stage based on its dependencies. Also takes care of priorities by marking any task further down the tree with the highest priority it's seen so far."""
    stage_complete = stage.get("complete", False)

    for from_node, to_node in G.in_edges(stage["title"]):
        if not from_node in by_title:
            raise ValueError(
                f"Node '{from_node}' not found. This indicates a dependency on a stage that is not defined."
            )
        from_node_stage = by_title[from_node]
        if complete_is_tree and stage_complete:
            from_node_stage["complete"] = True

        # Patch the priority as the highest seen so far in order to correctly
        # prioritize the stages.
        if not updating_yaml:
            stage_priority = stage.get("priority", None)
            from_node_stage_priority = from_node_stage.get("priority", None)
            if (stage_priority is not None) and (
                (
                    (from_node_stage_priority is None)
                    or from_node_stage_priority < stage_priority
                )
            ):
                from_node_stage["priority"] = stage_priority
        walk_the_tree(
            G=G,
            by_title=by_title,
            stage=from_node_stage,
            complete_is_tree=complete_is_tree,
            updating_yaml=updating_yaml,
        )


def node_priority_for_sorting(*, node, by_title):
    """Returns the priority for sorting nodes in topological sort."""
    # If a custom priority is set, use it.
    stage = by_title[node]
    if "priority" in stage:
        # Reverse the priority for sorting purposes, so that higher priority stages come first.
        return -stage["priority"]

    # If the node is a leaf, it has the lowest priority (1).
    # Otherwise, it has a higher priority (0).
    return 1 if is_leaf(node) else 0


def topological_sort(*, project, complete_is_tree, updating_yaml):
    G = nx.DiGraph()
    by_title = {}
    sort_stage(
        G=G,
        by_title=by_title,
        parent_stage=None,
        stage=project,
        parallel=False,
    )

    # We always walk the tree to sort out priorities. We also take care of
    # complete_is_tree here.
    walk_the_tree(
        G=G,
        by_title=by_title,
        stage=project,
        complete_is_tree=complete_is_tree,
        updating_yaml=updating_yaml,
    )
    # TODO: Test and handle failure caused by depending on a stage that is not defined
    # TODO: Test and handle cycles in the graph
    # TODO: Check that nothing depends on the project stage itself

    stages = list(
        [
            by_title[title]
            for title in nx.lexicographical_topological_sort(
                G, key=lambda n: node_priority_for_sorting(node=n, by_title=by_title)
            )
        ]
    )

    return (
        G,
        by_title,
        stages,
    )
