from collections import defaultdict
from datetime import datetime
from multiprocessing import Process
from os import PathLike, makedirs
from time import sleep

from matplotlib import dates as mdates
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
        self._process: Process = Process(target=self._run, name="Resource Monitor", daemon=True)
        self._timestamps: list[datetime] = []
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
        makedirs(self._report_dir, exist_ok=True)
        if not self._timestamps:
            return
        fig, ax = plt.subplots(figsize=(12, 6))
        for device, values in sorted(self._cpu_util.items()):
            if values:
                xs = self._timestamps[-len(values):]
                ax.plot(xs, values, label=f"CPU {device} {self._cpu_names.get(device, '')} utilization")
        for device, values in sorted(self._cpu_mem_util.items()):
            if values:
                xs = self._timestamps[-len(values):]
                ax.plot(xs, values, linestyle="--", label=f"CPU {device} memory utilization")
        for device, values in sorted(self._gpu_util.items()):
            if values:
                xs = self._timestamps[-len(values):]
                ax.plot(xs, values, label=f"GPU {device} {self._gpu_names.get(device, '')} utilization")
        for device, values in sorted(self._gpu_mem_util.items()):
            if values:
                xs = self._timestamps[-len(values):]
                ax.plot(xs, values, linestyle="--", label=f"GPU {device} memory utilization")
        ax.set_xlabel("Time")
        ax.set_ylabel("Utilization (%)")
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(path)
        plt.close(fig)

    def _run(self) -> None:
        while True:
            self._timestamps.append(datetime.now())
            for device, info in get_all_cpu_info().items():
                self._cpu_names[device] = info.name
                self._cpu_util[device].append(info.utilization_percent)
                self._cpu_mem_util[device].append(info.memory_utilization_percent)
            for device, info in get_all_gpu_info().items():
                self._gpu_names[device] = info.name
                self._gpu_util[device].append(info.utilization_percent)
                self._gpu_mem_util[device].append(info.memory_utilization_percent)
            self.make_plots(f"{self._report_dir}/{self._timestamps[0].strftime('%Y-%m-%d_%H:%M:%S')}.png")
            sleep(self._interval)

    def start(self) -> None:
        makedirs(self._report_dir, exist_ok=True)
        if not self._process.is_alive():
            self._process.start()
