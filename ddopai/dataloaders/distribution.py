"""Dataloaders that return data by sampling from some pre-defined distributions."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/10_dataloaders/11_distribution_loaders.ipynb.

# %% auto 0
__all__ = ['BaseDistributionDataLoader', 'NormalDistributionDataLoader']

# %% ../../nbs/10_dataloaders/11_distribution_loaders.ipynb 3
import numpy as np
from abc import ABC, abstractmethod
from typing import Union

from .base import BaseDataLoader

# %% ../../nbs/10_dataloaders/11_distribution_loaders.ipynb 4
class BaseDistributionDataLoader(BaseDataLoader):

    is_distribution = True

    def __init__(self):
        super().__init__()

# %% ../../nbs/10_dataloaders/11_distribution_loaders.ipynb 5
class NormalDistributionDataLoader(BaseDistributionDataLoader):

    """
    A dataloader that generates a dataset of normally distributed values.
    """
    
    def __init__(self,
        mean: float,
        std: float,
        num_units: int,
        truncated_low: int = 0,
        truncated_high: int = None #
    ):
        self.num_units = num_units
        self.mean = mean
        self.std = std
        self.truncated_low = truncated_low
        self.truncated_high = truncated_high

        self.val_index_start = 0 # No special validation set, necessary such that dataloader.val() does not throw an error
        self.test_index_start = 0  # No special test set, necessary such that dataloader.test() does not throw an error
        
        super().__init__()
    
    def __getitem__(self, idx):

        """
    
        Samples a datapoint from the distribution. As the distribution is generated on the fly, the index is not used.
        """

        Y = np.random.normal(self.mean, self.std, self.num_units)

        if self.truncated_low is not None:
            Y = np.maximum(Y, self.truncated_low)
        if self.truncated_high is not None:
            Y = np.minimum(Y, self.truncated_high)

        return None, Y

    def __len__(self):
        """
        Returns the length of the distribution. As the distribution is generated on the fly, the length is not defined.
        """
        raise ValueError('Length of a distribution is not defined')

    @property
    def X_shape(self):
        return None

    @property
    def Y_shape(self):
        return (1, self.num_units)
 
    def get_all_X(self):

        """
        Returns the entire features dataset. If no X data is available, return None.
        """
        return None

    def get_all_Y(self):

        """
        Returns the entire target dataset. If no Y data is available, return None.
        """
        return None

    @property
    def len_train(self):
        return np.inf

    @property
    def len_val(self):
        return np.inf

    @property
    def len_test(self):
        return np.inf
