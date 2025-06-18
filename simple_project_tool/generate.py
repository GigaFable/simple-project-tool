import sys
import argparse
from .mermaid_utilities import generate_mermaid
from .order_of_work import order_of_work
from .yaml_utilities import parse_yaml, update_yaml


def main():
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
        update_yaml(project=project, complete_is_tree=args.complete_is_tree)
    else:
        if args.incomplete_only:
            print("The --incomplete-only option is not supported for Mermaid output.")
            sys.exit(1)
        generate_mermaid(project=project, complete_is_tree=args.complete_is_tree)


if __name__ == "__main__":
    main()
