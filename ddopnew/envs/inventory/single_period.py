# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../nbs/21_envs_inventory/20_single_period_envs.ipynb.

# %% auto 0
__all__ = ['NewsvendorEnv', 'NewsvendorEnvVariableSL']

# %% ../../../nbs/21_envs_inventory/20_single_period_envs.ipynb 3
from abc import ABC, abstractmethod
from typing import Union, Tuple

from ...utils import Parameter, MDPInfo
from ...dataloaders.base import BaseDataLoader
from ...loss_functions import pinball_loss
from .base import BaseInventoryEnv

import gymnasium as gym

import numpy as np
import time

# %% ../../../nbs/21_envs_inventory/20_single_period_envs.ipynb 4
class NewsvendorEnv(BaseInventoryEnv, ABC):
    
    """
    Class implementing the Newsvendor problem, working for the single- and multi-item case. If underage_cost and overage_cost
    are scalars and there are multiple SKUs, then the same cost is used for all SKUs. If underage_cost and overage_cost are arrays,
    then they must have the same length as the number of SKUs. Num_SKUs can be set as parameter or inferred from the DataLoader.
    """

    def __init__(self,
        underage_cost: Union[np.ndarray, Parameter, int, float] = 1, # underage cost per unit
        overage_cost: Union[np.ndarray, Parameter, int, float] = 1, # overage cost per unit
        q_bound_low: Union[np.ndarray, Parameter, int, float] = 0, # lower bound of the order quantity
        q_bound_high: Union[np.ndarray, Parameter, int, float] = np.inf, # upper bound of the order quantity
        dataloader: BaseDataLoader = None, # dataloader
        num_SKUs: Union[int] = None, # if None it will be inferred from the DataLoader
        gamma: float = 1, # discount factor
        horizon_train: int | str = "use_all_data", # if "use_all_data" then horizon is inferred from the DataLoader
        postprocessors: list[object] | None = None,  # default is empty list
        mode: str = "train", # Initial mode (train, val, test) of the environment
        return_truncation: str = True # whether to return a truncated condition in step function
    ) -> None:

        self.print=False

        num_SKUs = dataloader.num_units if num_SKUs is None else num_SKUs
        if not isinstance(num_SKUs, int):
            raise ValueError("num_SKUs must be an integer.")
        
        self.set_param("num_SKUs", num_SKUs, shape=(1,), new=True)

        self.set_param("q_bound_low", q_bound_low, shape=(num_SKUs,), new=True)
        self.set_param("q_bound_high", q_bound_high, shape=(num_SKUs,), new=True)

        self.set_observation_space(dataloader.X_shape)
        self.set_action_space(dataloader.Y_shape, low = self.q_bound_low, high = self.q_bound_high)
        
        mdp_info = MDPInfo(self.observation_space, self.action_space, gamma=gamma, horizon=horizon_train)
        
        super().__init__(mdp_info=mdp_info,
                            postprocessors = postprocessors, 
                            mode=mode, return_truncation=return_truncation,
                            underage_cost=underage_cost,
                            overage_cost=overage_cost, 
                            dataloader=dataloader,
                            horizon_train = horizon_train)
        
        

    def step_(self, 
            action: np.ndarray # order quantity
            ) -> Tuple[np.ndarray, float, bool, bool, dict]:

        """
        Step function implementing the Newsvendor logic. Note that the dataloader will return an observation and a demand,
        which will be relevant in the next period. The observation will be returned directly, while the demand will be 
        temporarily stored under self.demand and used in the next step.

        """

        # Most agent give by default a batch dimension which is not needed for a single period action.
        # If action shape size is 2 and the first dimensiion is 1, then remove it
        if action.ndim == 2 and action.shape[0] == 1:
            action = np.squeeze(action, axis=0)  # Remove the first dimension

        cost_per_SKU = pinball_loss(self.demand, action, self.underage_cost, self.overage_cost)
        reward = -np.sum(cost_per_SKU) # negative because we want to minimize the cost

        terminated = False # in this problem there is no termination condition
        
        info = dict(
            demand=self.demand.copy(),
            action=action.copy(),
            cost_per_SKU=cost_per_SKU.copy()
        )

        # Set index will set the index and return True if the index is out of bounds
        truncated = self.set_index()

        if truncated:

            # observation = np.zeros_like(self.observation_space.sample()) if self.observation_space is not None else None
            # demand = np.zeros_like(self.action_space.sample())

            observation, self.demand = self.get_observation()


            return observation, reward, terminated, truncated, info
        
        else:

            observation, self.demand = self.get_observation()

            if self.print:
                print("next_period:", self.index+1)
                print("next observation:", observation)
                print("next demand:", self.demand)
                time.sleep(3)

            return observation, reward, terminated, truncated, info

# %% ../../../nbs/21_envs_inventory/20_single_period_envs.ipynb 13
class NewsvendorEnvVariableSL(NewsvendorEnv, ABC):
    def __init__(self,
        underage_cost: Union[np.ndarray, Parameter, int, float] = 1, # underage cost per unit
        overage_cost: Union[np.ndarray, Parameter, int, float] = 1, # overage cost per unit
        q_bound_low: Union[np.ndarray, Parameter, int, float] = 0, # lower bound of the order quantity
        q_bound_high: Union[np.ndarray, Parameter, int, float] = np.inf, # upper bound of the order quantity
        dataloader: BaseDataLoader = None, # dataloader
        num_SKUs: Union[int] = None, # if None it will be inferred from the DataLoader
        gamma: float = 1, # discount factor
        horizon_train: int | str = "use_all_data", # if "use_all_data" then horizon is inferred from the DataLoader
        postprocessors: list[object] | None = None,  # default is empty list
        mode: str = "train", # Initial mode (train, val, test) of the environment
        return_truncation: str = True # whether to return a truncated condition in step function
    ) -> None:

        super.__init__(underage_cost=underage_cost,
                        overage_cost=overage_cost,
                        q_bound_low=q_bound_low,
                        q_bound_high=q_bound_high,
                        dataloader=dataloader,
                        num_SKUs=num_SKUs,
                        gamma=gamma,
                        horizon_train=horizon_train,
                        postprocessors=postprocessors,
                        mode=mode,
                        return_truncation=return_truncation)
