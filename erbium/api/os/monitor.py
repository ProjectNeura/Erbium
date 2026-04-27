from os import PathLike
from multiprocessing import Process
from collections import defaultdict

from matplotlib import pyplot as plt

from erbium.api.os.cpu import get_all_cpu_info
from erbium.api.os.gpu import get_all_gpu_info


class ResourceMonitor(object):
    def __init__(self, report_dir: str | PathLike[str], *, interval: float = 10) -> None:
        """
        :param report_dir: directory to save the report files
        :param interval: interval of getting GPU info in seconds
        """
        self._report_dir: str = str(report_dir)
        self._interval: float = interval
        self._process: Process = Process(target=self._run, name="Resource Monitor")
        self._cpu_names: dict[int, str] = {device: info.name for device, info in get_all_cpu_info().items()}
        self._cpu_util: dict[int, list[float]] = defaultdict(list)
        self._cpu_mem_util: dict[int, list[float]] = defaultdict(list)
        self._gpu_names: dict[int, str] = {device: info.name for device, info in get_all_gpu_info().items()}
        self._gpu_util: dict[int, list[float]] = defaultdict(list)
        self._gpu_mem_util: dict[int, list[float]] = defaultdict(list)

    def make_plots(self, path: str | PathLike[str]) -> None:
        """
        Generate an integrated plot of CPU and GPU (memory) utilization rates.
        :param path: path to save the plot
        """
        path = str(path)
        plt.figure(figsize=(12, 6))
        for device, values in sorted(self._cpu_util.items()):
            if values:
                plt.plot(values, label=f"CPU {device} {self._cpu_names.get(device, '')} utilization")
        for device, values in sorted(self._cpu_mem_util.items()):
            if values:
                plt.plot(values, linestyle="--", label=f"CPU {device} memory utilization")
        for device, values in sorted(self._gpu_util.items()):
            if values:
                plt.plot(values, label=f"GPU {device} {self._gpu_names.get(device, '')} utilization")
        for device, values in sorted(self._gpu_mem_util.items()):
            if values:
                plt.plot(values, linestyle="--", label=f"GPU {device} memory utilization")
        plt.xlabel(f"Samples, one sample every {self._interval:g} seconds")
        plt.ylabel("Utilization (%)")
        plt.ylim(0, 100)
        plt.grid(True, alpha=.3)
        plt.legend(loc="best")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()

    def _run(self) -> None:
        for device, info in get_all_cpu_info().items():
            self._cpu_util[device].append(info.utilization_percent)
            self._cpu_mem_util[device].append(info.memory_utilization_percent)
        for device, info in get_all_gpu_info().items():
            self._gpu_util[device].append(info.utilization_percent)
            self._gpu_mem_util[device].append(info.memory_utilization_percent)
        self.make_plots(f"{self._report_dir}/util.png")

    def start(self) -> None:
        if not self._process.is_alive():
            self._process.start()
