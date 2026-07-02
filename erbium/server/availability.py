from dataclasses import asdict
from typing import Any, Mapping


def availability_payload(node: Any, gpu_infos: Mapping[int, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(device_id): {
            "available": node.is_available(info),
            **asdict(info),
        }
        for device_id, info in gpu_infos.items()
    }
