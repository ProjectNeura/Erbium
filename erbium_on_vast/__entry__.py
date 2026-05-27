from argparse import ArgumentParser

from erbium_on_vast.functional import initialize, upload_workspace


def __entry__() -> None:
    parser = ArgumentParser(prog="Erbium on Vast", description="Erbium Compute Platform on Vast.ai",
                            epilog="GitHub: https://github.com/ProjectNeura/Erbium")
    subparsers = parser.add_subparsers(dest="action", required=True)
    docker_parser = subparsers.add_parser("init")
    docker_parser.add_argument("node_id", required=True, help="The ID of this node")
    args = parser.parse_args()
    match args.action:
        case "init":
            initialize(args.init)
        case "upload":
            upload_workspace()
