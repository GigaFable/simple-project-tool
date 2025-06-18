from rich.console import Console
from sort_utilities import topological_sort
from general_utilities import is_leaf


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
