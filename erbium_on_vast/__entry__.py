from argparse import ArgumentParser

from erbium_on_vast.functional import initialize, upload_workspace, download_workspace, remove_workspace


def __entry__() -> None:
    parser = ArgumentParser(prog="Erbium on Vast", description="Erbium Compute Platform on Vast.ai",
                            epilog="GitHub: https://github.com/ProjectNeura/Erbium")
    subparsers = parser.add_subparsers(dest="action", required=True)
    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("node_id", help="The ID of this node")
    init_parser.add_argument("--hf_token", required=True, help="The Hugging Face token")
    upload_parser = subparsers.add_parser("upload")
    upload_parser.add_argument("--workspace", default="/workspace", help="The path to the workspace directory")
    upload_parser.add_argument("--hf_bucket", default="ProjectNeura/ErbiumOnVast",
                               help="The Hugging Face bucket to upload the workspace to")
    upload_parser.add_argument("--ignore", nargs="+", default=[], help="Patterns to ignore when uploading the workspace")
    download_parser = subparsers.add_parser("download")
    download_parser.add_argument("--workspace", default="/workspace", help="The path to the workspace directory")
    download_parser.add_argument("--hf_bucket", default="ProjectNeura/ErbiumOnVast",
                                 help="The Hugging Face bucket to download the workspace from")
    remove_parser = subparsers.add_parser("remove")
    remove_parser.add_argument("--node_id", default=None, help="The ID of the node to remove")
    remove_parser.add_argument("--hf_bucket", default="ProjectNeura/ErbiumOnVast",
                                 help="The Hugging Face bucket to download the workspace from")
    args = parser.parse_args()
    match args.action:
        case "init":
            initialize(args.node_id, args.hf_token)
        case "upload":
            upload_workspace(args.ignore, workspace=args.workspace, hf_bucket=args.hf_bucket)
        case "download":
            download_workspace(workspace=args.workspace, hf_bucket=args.hf_bucket)
        case "remove":
            remove_workspace(node_id=args.node_id, hf_bucket=args.hf_bucket)
