def command_to_initialize_docker(cloudflared_tunnel_token: str, *, shared_network: str = "labnet") -> str:
    return f"docker network inspect {shared_network} >/dev/null 2>&1 || docker network create {shared_network}; docker run -d --name cloudflared --network {shared_network} cloudflare/cloudflared:latest tunnel run --token {cloudflared_tunnel_token}"
