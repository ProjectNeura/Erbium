from argparse import ArgumentParser

from erbium.api import create_docker_compose, command_to_start_docker_compose, run_command, command_to_initialize_docker
from erbium.api.docker.docker_compose import __DEFAULT_BASE_IMAGE__, __DEFAULT_SHARED_NETWORK__
from erbium.server.run import run_server


def __entry__() -> None:
    parser = ArgumentParser(prog="Erbium", description="Erbium Compute Platform",
                            epilog="GitHub: https://github.com/ProjectNeura/Erbium")
    subparsers = parser.add_subparsers(dest="system", required=True)
    docker_parser = subparsers.add_parser("docker")
    docker_sub = docker_parser.add_subparsers(dest="docker_cmd", required=True)
    docker_init = docker_sub.add_parser("init")
    docker_init.add_argument("-n", "--shared_network", default=__DEFAULT_SHARED_NETWORK__)
    docker_init.add_argument("--protocol", choices=["quic", "http2"], default="quic")
    docker_create = docker_sub.add_parser("create")
    docker_create.add_argument("-n", "--service_name", required=True)
    docker_create.add_argument("-p", "--password", required=True)
    docker_create.add_argument("-b", "--base_image", default=__DEFAULT_BASE_IMAGE__)
    docker_create.add_argument("--gpus", nargs="+", default=["all"], help="List of GPU IDs to use, or \"all\" for all available GPUs")
    docker_create.add_argument("--no-backup", action="store_true", help="Disable automatic Borg backups for the output directory")
    docker_create.add_argument("paths", nargs="+",
                               help="INPUT_DIR OUTPUT_DIR BACKUP_DIR SAVE_AS, or INPUT_DIR OUTPUT_DIR SAVE_AS with --no-backup")
    docker_run = docker_sub.add_parser("run")
    docker_run.add_argument("profile_path")
    docker_run.add_argument("service_name")
    docker_run.add_argument("-f", "--force_build", action="store_true")
    server_parser = subparsers.add_parser("server")
    server_sub = server_parser.add_subparsers(dest="server_cmd", required=True)
    server_run = server_sub.add_parser("run")
    server_run.add_argument("-p", "--port", type=int, default=8000)
    server_run.add_argument("--host", default="0.0.0.0")
    server_run.add_argument("--max_gpu_utilization", type=float, default=.1)
    server_run.add_argument("--max_run_time_hrs", type=float, default=168)
    server_run.add_argument("--log_level", default="warning", choices=["critical", "error", "warning", "info", "debug", "trace"])
    server_run.add_argument("--access_log", action="store_true")
    args = parser.parse_args()
    match args.system:
        case "docker":
            match args.docker_cmd:
                case "init":
                    with open("cloudflared_tunnel_token.txt") as f:
                        run_command(command_to_initialize_docker(f.read().strip(), protocol=args.protocol,
                                                                 shared_network=args.shared_network))
                case "create":
                    expected_path_count = 3 if args.no_backup else 4
                    if len(args.paths) != expected_path_count:
                        docker_create.error(
                            f"expected {expected_path_count} path arguments when "
                            f"{'--no-backup is set' if args.no_backup else '--no-backup is not set'}"
                        )
                    if args.no_backup:
                        input_dir, output_dir, save_as = args.paths
                        backup_dir = None
                    else:
                        input_dir, output_dir, backup_dir, save_as = args.paths
                    with open(save_as, "w") as f:
                        f.write(create_docker_compose(
                            args.service_name, args.password, base_image=args.base_image, hostname=args.service_name,
                            container_name=args.service_name, input_dir=input_dir, output_dir=output_dir,
                            backup_dir=backup_dir, gpus=args.gpus
                        ))
                case "run":
                    run_command(command_to_start_docker_compose(
                        args.profile_path, args.service_name, force_build=args.force_build
                    ))
        case "server":
            match args.server_cmd:
                case "run":
                    run_server(args.port, host=args.host, node_kwargs={
                        "max_gpu_utilization": args.max_gpu_utilization,
                        "max_run_time_hrs": args.max_run_time_hrs
                    }, log_level=args.log_level, access_log=args.access_log)
