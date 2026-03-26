from dataclasses import dataclass

from pynvml import nvmlInit, nvmlDeviceGetCount, nvmlDeviceGetHandleByIndex, nvmlDeviceGetName, \
    nvmlDeviceGetClockInfo, NVML_CLOCK_GRAPHICS, NVML_CLOCK_MEM, nvmlDeviceGetMemoryInfo, nvmlDeviceGetFanSpeed, \
    nvmlDeviceGetUtilizationRates, nvmlDeviceGetPowerUsage


@dataclass
class GPUInfo(object):
    device_id: int
    name: str
    utilization_percent: float
    memory_utilization_percent: float
    power_draw_w: float
    clock_speed_mhz: float
    memory_clock_speed_mhz: float
    total_memory_gb: float
    fan_speed_percent: float


def get_all_gpu_info() -> dict[int, GPUInfo]:
    r = {}
    nvmlInit()
    device_count = nvmlDeviceGetCount()
    for i in range(device_count):
        handle = nvmlDeviceGetHandleByIndex(i)
        utilization_rates = nvmlDeviceGetUtilizationRates(handle)
        r[i] = GPUInfo(
            i, nvmlDeviceGetName(handle), utilization_rates.gpu, utilization_rates.memory,
            nvmlDeviceGetPowerUsage(handle) / 1000, nvmlDeviceGetClockInfo(handle, NVML_CLOCK_GRAPHICS),
            nvmlDeviceGetClockInfo(handle, NVML_CLOCK_MEM), nvmlDeviceGetMemoryInfo(handle).total / 1073741824,
            nvmlDeviceGetFanSpeed(handle),
        )
    return r
