# Erbium

## Introduction

Erbium is Project Neura's internal compute platform. It is designed to suit mid-scale organizational needs and 100%
open-source to avoid concerns about backdoors. We do not aim to provide a user system as it may get too complex and
needs greatly vary across organizations. Our main goal is to build a general solution for job scheduling and
orchestration. We bring these together using C++ integrated with Python running in Docker containers, and services
exposed via APIs.

Currently, we only considered hosts with Nvidia GPUs, as they are the most developer-friendly and widely used. You can
simply fork this repository and replace the driver-related code with your own.

## Install API

```shell
pip install git+https://github.com/ProjectNeura/Erbium
```

## Create a Docker Compose File

```shell
python -m docker create -n SERVICE_NAME -p SSH_PASSWORD INPUT_DIR OUTPUT_DIR SAVE_AS
```

## Initialize the Control Server

### Install `cloudflared`

#### Windows

```shell
winget install --id Cloudflare.cloudflared
```

#### Linux

```shell
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared noble main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt-get update
sudo apt-get install cloudflared
```

### Start Reverse Proxy

```shell
cloudflared tunnel login
cloudflared tunnel create ErbiumControl
cloudflared tunnel run ErbiumControl
```