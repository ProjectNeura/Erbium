from os import name


def command_to_initialize_docker(cloudflared_tunnel_token: str, *, shared_network: str = "labnet") -> str:
    if name == "nt":
        return f"docker network inspect {shared_network} >NUL 2>&1 || docker network create {shared_network} && docker rm -f cloudflared >NUL 2>&1 && docker run -d --name cloudflared --restart unless-stopped --network {shared_network} cloudflare/cloudflared:latest tunnel run --token {cloudflared_tunnel_token}"
    return f"(docker network inspect {shared_network} >/dev/null 2>&1 || docker network create {shared_network}) && (docker rm -f cloudflared >/dev/null 2>&1 || true) && (docker run -d --name cloudflared --restart unless-stopped --network {shared_network} cloudflare/cloudflared:latest tunnel run --token '{cloudflared_tunnel_token}')"
