# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../nbs/21_envs_inventory/10_base_inventory_env.ipynb.

# %% auto 0
__all__ = ['BaseInventoryEnv']

# %% ../../../nbs/21_envs_inventory/10_base_inventory_env.ipynb 3
from abc import ABC, abstractmethod
from typing import Union, Tuple

from ..base import BaseEnvironment
from ...utils import Parameter, MDPInfo
from ...dataloaders.base import BaseDataLoader
from ...loss_functions import pinball_loss

import gymnasium as gym

import numpy as np
import time

# %% ../../../nbs/21_envs_inventory/10_base_inventory_env.ipynb 4
class BaseInventoryEnv(BaseEnvironment):
    """
    Base class for inventory management environments. This class inherits from BaseEnvironment.
    
    """

    def __init__(self, 
        mdp_info: MDPInfo, #
        postprocessors: list[object] | None = None,  # default is empty list
        mode: str = "train", # Initial mode (train, val, test) of the environment
        return_truncation: str = True # whether to return a truncated condition in step function
        ) -> None:

        super().__init__(mdp_info=mdp_info, postprocessors = postprocessors,  mode = mode, return_truncation=return_truncation)
    
    def set_observation_space(self,
                            shape: tuple, # shape of the dataloader features
                            low: Union[np.ndarray, float] = -np.inf, # lower bound of the observation space
                            high: Union[np.ndarray, float] = np.inf, # upper bound of the observation space
                            samples_dim_included = True # whether the first dimension of the shape input is the number of samples
                            ) -> None:
        
        '''
        Set the observation space of the environment.
        This is a standard function for simple observation spaces. For more complex observation spaces,
        this function should be overwritten. Note that it is assumped that the first dimension
        is n_samples that is not relevant for the observation space.

        '''

        # To handle cases when no external information is available (e.g., parametric NV)
        
        if shape is None:
            self.observation_space = None

        else:
            if not isinstance(shape, tuple):
                raise ValueError("Shape must be a tuple.")
            
            if samples_dim_included:
                shape = shape[1:] # assumed that the first dimension is the number of samples

            self.observation_space = gym.spaces.Box(low=low, high=high, shape=shape, dtype=np.float32)

    def set_action_space(self,
                            shape: tuple, # shape of the dataloader target
                            low: Union[np.ndarray, float] = -np.inf, # lower bound of the observation space
                            high: Union[np.ndarray, float] = np.inf, # upper bound of the observation space
                            samples_dim_included = True # whether the first dimension of the shape input is the number of samples
                            ) -> None:
        
        '''
        Set the action space of the environment.
        This is a standard function for simple action spaces. For more complex action spaces,
        this function should be overwritten. Note that it is assumped that the first dimension
        is n_samples that is not relevant for the action space.
        '''

        if not isinstance(shape, tuple):
            raise ValueError("Shape must be a tuple.")
        
        if samples_dim_included:
            shape = shape[1:] # assumed that the first dimension is the number of samples

        self.action_space = gym.spaces.Box(low=low, high=high, shape=shape, dtype=np.float32)
    
    def get_observation(self):
        
        """
        Return the current observation. This function is for the simple case where the observation
        is only an x,y pair. For more complex observations, this function should be overwritten.

        """

        
        X_item, Y_item = self.dataloader[self.index]

        return X_item, Y_item
