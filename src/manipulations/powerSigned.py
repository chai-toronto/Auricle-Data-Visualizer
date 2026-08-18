from __future__ import annotations

import numpy as np

from src.manipulations.base import DataManipulation


class PowerManipulation(DataManipulation):
    name = "Power Signed"
    description = "Raise channel data to a power in the selected region while preserving the sign."
    options = {
        "exponent": {
            "type": "int",
            "label": "Exponent",
            "default": 2,
            "placeholder": 2,
        }
    }

    def apply(self, data, timestamps, channel_idx, region, option_values):
        result = data.copy()
        start, end = region
        mask = (timestamps >= start) & (timestamps <= end)
        segment = result[mask]
        seg_signs = np.sign(segment)
        if len(segment) == 0:
            return result

        result[mask] = seg_signs * (segment ** option_values.get("exponent", 2))

        return result
