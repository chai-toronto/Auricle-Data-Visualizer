"""Normalize manipulation: applies z-score or min-max normalization to a region."""
from __future__ import annotations

import numpy as np

from src.manipulations.base import DataManipulation


class SquareManipulation(DataManipulation):
    name = "Square"
    description = "Square channel data in the selected region."
    options = {

    }

    def apply(self, data, timestamps, channel_idx, region, option_values):
        result = data.copy()
        start, end = region
        mask = (timestamps >= start) & (timestamps <= end)
        segment = result[mask]
        if len(segment) == 0:
            return result

        result[mask] = segment ** 2

        return result
