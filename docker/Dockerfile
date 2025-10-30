FROM nvcr.io/nvidia/pytorch:25.10-py3
RUN python3.12 -m pip install git+https://github.com/ProjectNeura/Erbium.git
COPY app /workspace/code
WORKDIR /workspace/code
RUN python3.12 -m pip install -r requirements.txt
CMD ["bash", "main.sh"]