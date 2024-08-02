# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_utils/10_postprocessors.ipynb.

# %% auto 0
__all__ = ['ClipAction', 'RoundAction']

# %% ../nbs/00_utils/10_postprocessors.ipynb 3
from typing import Union, Optional

import numpy as np
from .utils import Parameter, check_parameter_types

import torch
import torch.nn as nn
import torch.nn.functional as F

# %% ../nbs/00_utils/10_postprocessors.ipynb 5
class ClipAction:
    """
    A class to clip input values within specified bounds.
    """

    def __init__(self, lower: Optional[Union[float, np.ndarray]] = None, upper: Optional[Union[float, np.ndarray]] = None):
        self.lower = self._convert_to_array(lower)
        self.upper = self._convert_to_array(upper)

    def _convert_to_array(self, value: Optional[Union[float, np.ndarray]]) -> Optional[np.ndarray]:
        """
        Converts a float value to a numpy array of shape (1,) if needed.
        """
        if value is None:
            return None
        if isinstance(value, float):
            return np.array([value])
        if isinstance(value, np.ndarray):
            return value
        raise TypeError(f"Bounds must be float or np.ndarray, got {type(value).__name__}")

    def __call__(self, input: np.ndarray) -> np.ndarray:
        """
        Clips the input array within the specified bounds.

        Parameters:
        - input: A numpy array to be clipped.

        Returns:
        - A numpy array with values clipped within the specified bounds.
        """
        
        check_parameter_types(input)

        # Ensure bounds match the input's shape if they are arrays
        if self.lower is not None and self.lower.size != 1 and self.lower.shape != input.shape:
            raise ValueError("Lower bound array must match the input shape or be a single element")

        if self.upper is not None and self.upper.size != 1 and self.upper.shape != input.shape:
            raise ValueError("Upper bound array must match the input shape or be a single element")

        # Perform clipping
        output = np.clip(input, a_min=self.lower, a_max=self.upper)

        return output

# %% ../nbs/00_utils/10_postprocessors.ipynb 6
class RoundAction:
    """
    A class to round input values to the nearest specified unit size.
    """

    def __init__(self, unit_size: Union[float, int, np.ndarray]):
        self.unit_size = self._validate_unit_size(unit_size)

    def _validate_unit_size(self, unit_size: Union[float, int, np.ndarray]) -> np.ndarray:
        """
        Ensures that the unit size is a positive float, int, or a numpy array of positive values.
        """
        if isinstance(unit_size, (float, int)):
            if unit_size <= 0:
                raise ValueError("Unit size must be a positive number")
            return np.array([unit_size], dtype=float)  # Convert to float for consistent behavior
        elif isinstance(unit_size, np.ndarray):
            if np.any(unit_size <= 0):
                raise ValueError("All elements of unit size array must be positive")
            return unit_size.astype(float)  # Ensure numpy array is of float type
        else:
            raise TypeError("Unit size must be a float, int, or np.ndarray")

    def __call__(self, input: np.ndarray) -> np.ndarray:
        """
        Rounds the input array to the nearest specified unit size.

        Parameters:
        - input: A numpy array to be rounded.

        Returns:
        - A numpy array with values rounded to the nearest specified unit size.
        """
        
        check_parameter_types(input)

        # Ensure unit_size matches the input's shape if it is an array
        if self.unit_size.size != 1 and self.unit_size.shape != input.shape:
            raise ValueError("Unit size array must match the input shape or be a single element")

        # Perform rounding
        output = np.round(input / self.unit_size) * self.unit_size

        return output
