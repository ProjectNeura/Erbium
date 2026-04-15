# Erbium

## Introduction

Erbium is Project Neura's internal compute platform. It is designed to suit mid-scale organizational needs and 100%
open-source to avoid concerns about backdoors. We do not aim to provide a user system as it may get too complex and
needs greatly vary across organizations. Our main goal is to build a general solution for job scheduling and
orchestration. We bring these together using C++ integrated with Python running in Docker containers, and services
exposed via APIs.

Currently, we only considered hosts with Nvidia GPUs, as they are the most developer-friendly and widely used. You can
simply fork this repository and replace the driver-related code with your own.

## Key Features

- SSH Tunneling
- JupyterLab
- Job Scheduling
- File History Backup

## Setting Up Your Workstation as a Host

### Clone the Repository

```shell
git clone https://github.com/ProjectNeura/Erbium
```

### Set Up Cloudflare Tunnel

You need to save the Cloudflare Tunnel token locally as "cloudflared_tunnel_token.txt" in the root directory of the
project.

Then, run the following command to start the tunnel:

```shell
python -m erbium docker init
```

### Build a Docker Image

```shell
python -m erbium docker create -n SERVICE_NAME -p SSH_PASSWORD INPUT_DIR OUTPUT_DIR ./docker-compose.yaml
```

### Start the Docker Container

```shell
python -m erbium docker run ./docker-compose.yaml SERVICE_NAME
```