from argparse import ArgumentParser
from os.path import exists
from subprocess import run


def __entry__() -> None:
    parser = ArgumentParser(prog="Erbium", description="Erbium Compute Platform",
                            epilog="GitHub: https://github.com/ProjectNeura/Erbium")
    args = parser.parse_args()
    match args.action:
        case "pack":
            if not exists(f"{args.target}/Dockerfile"):
                raise FileNotFoundError(f"Dockerfile not found in {args.target}")
            run(("docker", "build", "-t", f"erbium:{args.version}", args.target))
        case "run":
            version = args.version if args.version else "latest"
            if not exists(args.input):
                raise FileNotFoundError(f"Input directory not found: {args.input}")
            if not exists(args.output):
                raise FileNotFoundError(f"Output directory not found: {args.output}")
            commands = [
                "docker", "run", "--ipc=host", "--ulimit", "memlock=-1", "--ulimit", "stack=67108864", "--gpus",
                args.gpus, "-v", f"{args.input}:/workspace/input:ro", "-v", f"{args.output}:/workspace/output",
                f"erbium:{version}"
            ]
            if args.temporary:
                commands.insert(3, "--rm")
            run(commands)
