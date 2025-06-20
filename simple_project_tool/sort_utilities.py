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


def complete_tree(*, G, by_title, stage, complete):
    if complete:
        stage["complete"] = True
    for from_node, to_node in G.in_edges(stage["title"]):
        from_node_stage = by_title[from_node]
        complete_tree(
            G=G,
            by_title=by_title,
            stage=from_node_stage,
            complete=from_node_stage.get("complete", False)
            or stage.get("complete", False),
        )


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

    stages = list(
        [
            by_title[title]
            for title in nx.lexicographical_topological_sort(
                G, key=lambda n: 1 if is_leaf(by_title[n]) else 0
            )
        ]
    )

    if complete_is_tree:
        complete_tree(
            G=G,
            by_title=by_title,
            stage=project,
            complete=project.get("complete", False),
        )
    # TODO: Test and handle failure caused by depending on a stage that is not defined
    # TODO: Test and handle cycles in the graph
    # TODO: Check that nothing depends on the project stage itself
    return (
        G,
        by_title,
        stages,
    )
