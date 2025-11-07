from argparse import ArgumentParser
from os.path import exists
from subprocess import run


def __entry__() -> None:
    parser = ArgumentParser(prog="Erbium CLI", description="Erbium Command Line Interface",
                            epilog="GitHub: https://github.com/ProjectNeura/Erbium")
    parser.add_argument("action", choices=("pack", "run"))
    parser.add_argument("-v", "--version", default="latest", help="version of Erbium image")
    parser.add_argument("-i", "--input", default="P:/SharedDatasets", help="path to shared datasets")
    parser.add_argument("-o", "--output", default="P:/SharedWeights/Erbium", help="path to shared weights")
    parser.add_argument("--temporary", action="store_true", help="remove container after execution")
    parser.add_argument("-t", "--target", default=None, help="path to target directory")
    args = parser.parse_args()
    match args.action:
        case "pack":
            target = args.target if args.target else "docker"
            if not exists(f"{target}/Dockerfile"):
                raise FileNotFoundError(f"Dockerfile not found in {args.target}")
            run(("docker", "build", "-t", f"erbium:{args.version}", target))
        case "run":
            version = args.version if args.version else "latest"
            if not exists(args.input):
                raise FileNotFoundError(f"Input directory not found: {args.input}")
            if not exists(args.output):
                raise FileNotFoundError(f"Output directory not found: {args.output}")
            commands = [
                "docker", "run", "--ipc=host", "--gpus", "all", "-v", f"{args.input}:/workspace/input:ro", "-v",
                f"{args.output}:/workspace/output", f"erbium:{version}"
            ]
            if args.temporary:
                commands.insert(3, "--rm")
            run(commands)
