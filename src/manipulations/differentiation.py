"""Differentiation manipulation: differentiates channel data in the selected region."""
from __future__ import annotations

import numpy as np

from src.manipulations.base import DataManipulation


class DifferentiationManipulation(DataManipulation):
    name = "Differentiation"
    description = "Differentiate channel data in the selected region."
    options = {
        "dx": {
            "type": "int",
            "label": "dx",
            "default": 1,
            "placeholder": 1,
        }
    }

    def apply(self, data, timestamps, channel_idx, region, option_values):
        result = data.copy()
        start, end = region
        mask = (timestamps >= start) & (timestamps <= end)
        segment = result[mask]
        if len(segment) == 0:
            return result

        result[mask] = np.diff(segment, prepend=segment[0], dx=option_values.get("dx", 1))

        return result
