from argparse import ArgumentParser

from erbium.api import create_docker_compose, command_to_start_docker_compose, run_command, command_to_initialize_docker
from erbium.api.docker.docker_compose import __DEFAULT_BASE_CONTAINER__, __DEFAULT_SHARED_NETWORK__
from erbium.server.run import run_server


def __entry__() -> None:
    parser = ArgumentParser(prog="Erbium", description="Erbium Compute Platform",
                            epilog="GitHub: https://github.com/ProjectNeura/Erbium")
    subparsers = parser.add_subparsers(dest="system", required=True)
    docker_parser = subparsers.add_parser("docker")
    docker_sub = docker_parser.add_subparsers(dest="docker_cmd", required=True)
    docker_init = docker_sub.add_parser("init")
    docker_init.add_argument("-n", "--shared_network", default=__DEFAULT_SHARED_NETWORK__)
    docker_create = docker_sub.add_parser("create")
    docker_create.add_argument("-n", "--service_name", required=True)
    docker_create.add_argument("-b", "--base_container", default=__DEFAULT_BASE_CONTAINER__)
    docker_create.add_argument("input_dir")
    docker_create.add_argument("output_dir")
    docker_create.add_argument("save_as")
    docker_run = docker_sub.add_parser("run")
    docker_run.add_argument("profile_path")
    docker_run.add_argument("service_name")
    docker_run.add_argument("-f", "--force_build", action="store_true")
    server_parser = subparsers.add_parser("server")
    server_sub = server_parser.add_subparsers(dest="server_cmd", required=True)
    server_run = server_sub.add_parser("run")
    server_run.add_argument("-p", "--port", type=int, default=8000)
    server_run.add_argument("--host", default="0.0.0.0")
    server_run.add_argument("root_dir")
    server_run.add_argument("input_dir")
    server_run.add_argument("--max_gpu_utilization", type=float, default=.1)
    server_run.add_argument("--max_run_time_hrs", type=float, default=168)
    args = parser.parse_args()
    match args.system:
        case "docker":
            match args.docker_cmd:
                case "init":
                    with open("cloudflared_tunnel_token.txt") as f:
                        run_command(command_to_initialize_docker(f.read().strip(), shared_network=args.shared_network))
                case "create":
                    with open(args.save_as, "w") as f:
                        f.write(create_docker_compose(
                            args.service_name, base_container=args.base_container, input_dir=args.input_dir,
                            output_dir=args.output_dir
                        ))
                case "run":
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
