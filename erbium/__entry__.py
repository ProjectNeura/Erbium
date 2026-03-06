from argparse import ArgumentParser

from erbium.api import create_docker_compose, command_to_start_docker_compose, run_command
from erbium.api.docker.docker_compose import __DEFAULT_BASE_CONTAINER__
from erbium.server.run import run_server


def __entry__() -> None:
    parser = ArgumentParser(prog="Erbium", description="Erbium Compute Platform",
                            epilog="GitHub: https://github.com/ProjectNeura/Erbium")
    subparsers = parser.add_subparsers(dest="system", required=True)
    compose_parser = subparsers.add_parser("compose")
    compose_sub = compose_parser.add_subparsers(dest="compose_cmd", required=True)
    compose_create = compose_sub.add_parser("create")
    compose_create.add_argument("-n", "--service_name", required=True)
    compose_create.add_argument("-b", "--base_container", default=__DEFAULT_BASE_CONTAINER__)
    compose_create.add_argument("input_dir", required=True)
    compose_create.add_argument("output_dir", required=True)
    compose_create.add_argument("save_as", required=True)
    compose_up = compose_sub.add_parser("up")
    compose_up.add_argument("profile_path", required=True)
    compose_up.add_argument("service_name", required=True)
    compose_up.add_argument("-f", "--force_build", action="store_true")
    server_parser = subparsers.add_parser("server")
    server_sub = server_parser.add_subparsers(dest="server_cmd", required=True)
    server_run = server_sub.add_parser("run")
    server_run.add_argument("-p", "--port", type=int, default=8000)
    server_run.add_argument("-h", "--host", default="0.0.0.0")
    server_run.add_argument("root_dir", required=True)
    server_run.add_argument("input_dir", required=True)
    server_run.add_argument("max_gpu_utilization", type=float, default=.1)
    server_run.add_argument("max_run_time_hrs", type=float, default=168)
    args = parser.parse_args()
    match args.system:
        case "compose":
            match args.compose_cmd:
                case "create":
                    with open(args.save_as, "w") as f:
                        f.write(create_docker_compose(
                            args.service_name, base_container=args.base_container, input_dir=args.input_dir,
                            output_dir=args.output_dir
                        ))
                case "up":
                    run_command(command_to_start_docker_compose(
                        args.profile_path, args.service_name, force_build=args.force_build
                    ))
        case "server":
            match args.server_cmd:
                case "run":
                    run_server(args.port, args.root_dir, args.input_dir, host=args.host, scheduler_kwargs={
                        "max_gpu_utilization": args.max_gpu_utilization,
                        "max_run_time_hrs": args.max_run_time_hrs
                    })
