from dataclasses import dataclass

from pynvml import nvmlInit, nvmlDeviceGetCount, nvmlDeviceGetHandleByIndex, nvmlDeviceGetName, \
    nvmlDeviceGetClockInfo, NVML_CLOCK_GRAPHICS, NVML_CLOCK_MEM, nvmlDeviceGetMemoryInfo, nvmlDeviceGetFanSpeed, \
    nvmlDeviceGetUtilizationRates, nvmlDeviceGetPowerUsage, struct_c_nvmlDevice_t


@dataclass
class GPUInfo(object):
    device_id: int
    name: str
    utilization_percent: float
    memory_utilization_percent: float
    power_draw_w: float
    clock_speed_mhz: float | None
    memory_clock_speed_mhz: float | None
    total_memory_gb: float


def _clock_speed(handle: struct_c_nvmlDevice_t) -> float | None:
    try:
        return nvmlDeviceGetClockInfo(handle, NVML_CLOCK_GRAPHICS)
    except Exception:
        return None


def _mem_clock_speed(handle: struct_c_nvmlDevice_t) -> float | None:
    try:
        return nvmlDeviceGetClockInfo(handle, NVML_CLOCK_MEM)
    except Exception:
        return None


def get_all_gpu_info() -> dict[int, GPUInfo]:
    r = {}
    nvmlInit()
    device_count = nvmlDeviceGetCount()
    for i in range(device_count):
        handle = nvmlDeviceGetHandleByIndex(i)
        mem_info = nvmlDeviceGetMemoryInfo(handle)
        r[i] = GPUInfo(
            i, nvmlDeviceGetName(handle), nvmlDeviceGetUtilizationRates(handle).gpu,
            100 * mem_info.used / mem_info.total, nvmlDeviceGetPowerUsage(handle) / 1000,
            _clock_speed(handle), _mem_clock_speed(handle), mem_info.total / 1073741824
        )
    return r
