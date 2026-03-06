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