#include <nvml.h>

#include <atomic>
#include <chrono>
#include <csignal>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

struct GpuStat {
    unsigned int index = 0;
    std::string name;
    unsigned int max_gpu_util = 0;     // percent
    unsigned int max_mem_util = 0;     // percent
    unsigned long long max_mem_used = 0; // bytes
};

static std::atomic<bool> g_running(true);

void handle_signal(int) {
    g_running = false;
}

std::string escape_json(const std::string& s) {
    std::ostringstream oss;
    for (char c : s) {
        switch (c) {
            case '\"': oss << "\\\""; break;
            case '\\': oss << "\\\\"; break;
            case '\b': oss << "\\b"; break;
            case '\f': oss << "\\f"; break;
            case '\n': oss << "\\n"; break;
            case '\r': oss << "\\r"; break;
            case '\t': oss << "\\t"; break;
            default:
                if (static_cast<unsigned char>(c) < 0x20) {
                    oss << "\\u"
                        << std::hex << std::setw(4) << std::setfill('0')
                        << static_cast<int>(static_cast<unsigned char>(c))
                        << std::dec << std::setfill(' ');
                } else {
                    oss << c;
                }
        }
    }
    return oss.str();
}

std::string now_iso8601_utc() {
    std::time_t t = std::time(nullptr);
    std::tm tm_utc{};
#ifdef _WIN32
    gmtime_s(&tm_utc, &t);
#else
    gmtime_r(&t, &tm_utc);
#endif
    std::ostringstream oss;
    oss << std::put_time(&tm_utc, "%Y-%m-%dT%H:%M:%SZ");
    return oss.str();
}

bool write_json(const std::string& path,
                const std::vector<GpuStat>& stats,
                unsigned int interval_ms,
                const std::string& started_at,
                const std::string& updated_at) {
    std::ofstream out(path, std::ios::trunc);
    if (!out) {
        std::cerr << "Failed to open JSON file for writing: " << path << "\n";
        return false;
    }

    out << "{\n";
    out << "  \"started_at_utc\": \"" << escape_json(started_at) << "\",\n";
    out << "  \"updated_at_utc\": \"" << escape_json(updated_at) << "\",\n";
    out << "  \"poll_interval_ms\": " << interval_ms << ",\n";
    out << "  \"gpus\": [\n";

    for (size_t i = 0; i < stats.size(); ++i) {
        const auto& g = stats[i];
        out << "    {\n";
        out << "      \"index\": " << g.index << ",\n";
        out << "      \"name\": \"" << escape_json(g.name) << "\",\n";
        out << "      \"max_gpu_util_percent\": " << g.max_gpu_util << ",\n";
        out << "      \"max_memory_util_percent\": " << g.max_mem_util << ",\n";
        out << "      \"max_memory_used_bytes\": " << g.max_mem_used << "\n";
        out << "    }";
        if (i + 1 != stats.size()) out << ",";
        out << "\n";
    }

    out << "  ]\n";
    out << "}\n";

    return true;
}

int main() {
    const std::string output_path = "/workspace/output/gpu_max_utilization.json";
    const unsigned int poll_interval_ms = 1000;
    const unsigned int flush_every_n_polls = 5;

    std::signal(SIGINT, handle_signal);
    std::signal(SIGTERM, handle_signal);

    nvmlReturn_t result = nvmlInit();
    if (result != NVML_SUCCESS) {
        std::cerr << "nvmlInit() failed: " << nvmlErrorString(result) << "\n";
        return 1;
    }

    unsigned int device_count = 0;
    result = nvmlDeviceGetCount(&device_count);
    if (result != NVML_SUCCESS) {
        std::cerr << "nvmlDeviceGetCount() failed: " << nvmlErrorString(result) << "\n";
        nvmlShutdown();
        return 1;
    }

    if (device_count == 0) {
        std::cerr << "No NVIDIA GPUs found.\n";
        nvmlShutdown();
        return 1;
    }

    std::vector<nvmlDevice_t> devices(device_count);
    std::vector<GpuStat> stats(device_count);

    for (unsigned int i = 0; i < device_count; ++i) {
        result = nvmlDeviceGetHandleByIndex(i, &devices[i]);
        if (result != NVML_SUCCESS) {
            std::cerr << "nvmlDeviceGetHandleByIndex(" << i << ") failed: "
                      << nvmlErrorString(result) << "\n";
            nvmlShutdown();
            return 1;
        }

        char name_buf[NVML_DEVICE_NAME_BUFFER_SIZE] = {};
        result = nvmlDeviceGetName(devices[i], name_buf, NVML_DEVICE_NAME_BUFFER_SIZE);
        if (result != NVML_SUCCESS) {
            std::cerr << "nvmlDeviceGetName(" << i << ") failed: "
                      << nvmlErrorString(result) << "\n";
            nvmlShutdown();
            return 1;
        }

        stats[i].index = i;
        stats[i].name = name_buf;
    }

    const std::string started_at = now_iso8601_utc();
    unsigned long long poll_count = 0;

    std::cout << "Monitoring " << device_count << " GPU(s). Writing to "
              << output_path << ". Press Ctrl+C to stop.\n";

    while (g_running) {
        for (unsigned int i = 0; i < device_count; ++i) {
            nvmlUtilization_t util{};
            result = nvmlDeviceGetUtilizationRates(devices[i], &util);
            if (result == NVML_SUCCESS) {
                if (util.gpu > stats[i].max_gpu_util) {
                    stats[i].max_gpu_util = util.gpu;
                }
                if (util.memory > stats[i].max_mem_util) {
                    stats[i].max_mem_util = util.memory;
                }
            } else {
                std::cerr << "nvmlDeviceGetUtilizationRates(" << i << ") failed: "
                          << nvmlErrorString(result) << "\n";
            }

            nvmlMemory_t mem{};
            result = nvmlDeviceGetMemoryInfo(devices[i], &mem);
            if (result == NVML_SUCCESS) {
                if (mem.used > stats[i].max_mem_used) {
                    stats[i].max_mem_used = mem.used;
                }
            } else {
                std::cerr << "nvmlDeviceGetMemoryInfo(" << i << ") failed: "
                          << nvmlErrorString(result) << "\n";
            }
        }

        ++poll_count;

        if (poll_count % flush_every_n_polls == 0) {
            write_json(output_path, stats, poll_interval_ms, started_at, now_iso8601_utc());
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(poll_interval_ms));
    }

    write_json(output_path, stats, poll_interval_ms, started_at, now_iso8601_utc());
    nvmlShutdown();

    std::cout << "Final stats written to " << output_path << "\n";
    return 0;
}