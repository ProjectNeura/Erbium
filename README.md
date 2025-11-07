# Erbium

Project Neura's Internal Computing Platform

## Install API

```shell
pip install git+https://github.com/ProjectNeura/Erbium
```

## Pack

Write your dependencies in "docker/app/requirements.txt" and your main script in "docker/app/main.py".

```shell
erbium pack -v test -t docker
```

## Run

```shell
erbium run --temporary -i "/Volumes/Portable/SharedDatasets" -o "/Volumes/Portable/SharedWeights/Erbium" -v test
```