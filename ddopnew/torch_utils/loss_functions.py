"""Loss functions that are implemented in PyTorch"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/00_utils/20_torch_loss_functions.ipynb.

# %% auto 0
__all__ = ['quantile_loss', 'TorchQuantileLoss', 'pinball_loss', 'TorchPinballLoss']

# %% ../../nbs/00_utils/20_torch_loss_functions.ipynb 3
from typing import Union, Optional, Tuple

import numpy as np
from ..utils import Parameter

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.modules.loss import _Loss

import warnings

# %% ../../nbs/00_utils/20_torch_loss_functions.ipynb 4
def quantile_loss(
    input: torch.Tensor,
    target: torch.Tensor,
    quantile: torch.Tensor,
    reduction: str = 'mean',
) -> torch.Tensor:

    if not (target.size() == input.size()):
        warnings.warn(
            f"Using a target size ({target.size()}) that is different to the input size ({input.size()}). "
            "This will likely lead to incorrect results due to broadcasting. "
            "Please ensure they have the same size.",
            stacklevel=2,
        )

    expanded_input, expanded_target = torch.broadcast_tensors(input, target)

    # print(expanded_input.size(), expanded_target.size(), quantile.size())
    # print(quantile)

    loss = torch.max((expanded_target - expanded_input) * quantile, (expanded_input - expanded_target) * (1 - quantile))

    # print(losks.size())

    if reduction == 'mean':
        return loss.mean()
    elif reduction == 'sum':
        return loss.sum()
    else:
        raise ValueError(f"reduction={reduction} is not valid")

    return loss

# %% ../../nbs/00_utils/20_torch_loss_functions.ipynb 5
class TorchQuantileLoss(_Loss):

    """
    Implmentation of the quantile loss in Pytorch.
    Unlike the Numpy-based implementation ```quantile_loss``` in the loss_functions module, this implementation
    this implementation reduces the results to a scalar value using the specified reduction method. This class is 
    used to train Pytorch models using the quantile loss.
    """

    __constants__ = ['reduction']
    def __init__(self,reduction: str = 'mean') -> None: #
        super().__init__(reduction=reduction)

    def forward(self, input: torch.Tensor, target: torch.Tensor, quantile: Parameter | np.ndarray) -> torch.Tensor: #

        """
        Forward pass of the quantile loss function.

        """

        quantile = self.convert_quantile(quantile, input_dtype=input.dtype, device=input.device, target_shape = target.shape)
            
        if not (target.shape == input.shape == quantile.shape):
            warnings.warn(
                f"Mismatch in dimensions: target dimension ({target.shape}), input dimension ({input.shape}), "
                f"and quantile dimension ({quantile.shape}) must be the same. "
                "This will likely lead to incorrect results due to broadcasting. "
                "Please ensure they have the same size.",
                stacklevel=2,
            )

        return quantile_loss(input, target, quantile, reduction=self.reduction)
    
    def convert_quantile(self, quantile: Parameter | np.ndarray, input_dtype: torch.dtype = torch.float32, device: torch.device = torch.device('cpu'), target_shape: Tuple = None) -> torch.Tensor:
        
        if isinstance(quantile, Parameter):
            quantile =  quantile.get_value()
            
        if isinstance(quantile, np.ndarray):
            quantile = torch.tensor(quantile, dtype=input_dtype, device=device)
        elif isinstance(quantile, torch.Tensor):
            # ensure dtype and device are the same as the input tensor
            quantile = quantile.to(dtype=input_dtype, device=device)
        else:
            raise ValueError(f"quantile must be of type Parameter, np.ndarray, or torch.Tensor, but got {type(quantile)}")

        # check if quantile is of size 1:
        if quantile.size() == (1,):
            quantile = quantile.expand(target_shape)
        elif quantile.size() != target_shape:
            raise ValueError(f"quantile must be of size 1 or the same size as the target tensor, but got {quantile.size()} and {target_shape}")

        return quantile


# %% ../../nbs/00_utils/20_torch_loss_functions.ipynb 9
def pinball_loss(
    input: torch.Tensor,
    target: torch.Tensor,
    underage: torch.Tensor,
    overage: torch.Tensor,
    reduction: str = 'mean',
) -> torch.Tensor:

    if not (target.size() == input.size()):
        warnings.warn(
            f"Using a target size ({target.size()}) that is different to the input size ({input.size()}). "
            "This will likely lead to incorrect results due to broadcasting. "
            "Please ensure they have the same size.",
            stacklevel=2,
        )

    expanded_input, expanded_target = torch.broadcast_tensors(input, target)

    # loss = torch.max((expanded_target - expanded_input) * quantile, (expanded_input - expanded_target) * (1 - quantile))

    loss = torch.max(expanded_target - expanded_input, torch.tensor(0)) * underage + torch.max(expanded_input - expanded_target, torch.tensor(0)) * overage

    if reduction == 'mean':
        return loss.mean()
    elif reduction == 'sum':
        return loss.sum()
    else:
        raise ValueError(f"reduction={reduction} is not valid")

    return loss

# %% ../../nbs/00_utils/20_torch_loss_functions.ipynb 11
class TorchPinballLoss(_Loss):

    """
    Implmentation of the pinball loss in Pytorch using specific overage and underage cost. For the pinball loss
    based on quantiles directly, use the TorchQuantileLoss class.
    Unlike the Numpy-based implementation ```pinball_loss``` in the loss_functions module, this implementation
    this implementation reduces the results to a scalar value using the specified reduction method. This class is 
    used to train Pytorch models using the pinball loss.
    """

    __constants__ = ['reduction']
    def __init__(self,reduction: str = 'mean') -> None: #
        super().__init__(reduction=reduction)

    def forward(self, input: torch.Tensor, target: torch.Tensor, underage: Parameter | np.ndarray, overage: Parameter | np.ndarray) -> torch.Tensor: #

        """
        Forward pass of the pinball loss function.

        """

        underage = self.convert_cost_param(underage, input_dtype=input.dtype, device=input.device, target_shape = target.shape)
        overage = self.convert_cost_param(overage, input_dtype=input.dtype, device=input.device, target_shape = target.shape)
            
        if not (target.shape == input.shape == underage.shape == overage.shape):
            warnings.warn(
                f"Mismatch in dimensions: target dimension ({target.shape}), input dimension ({input.shape}), "
                f"underage dimension ({underage.shape}), and overage dimension ({overage.shape}) must be the same. "
                "This will likely lead to incorrect results due to broadcasting. "
                "Please ensure they have the same size.",
                stacklevel=2,
            )

        return pinball_loss(input, target, underage=underage, overage=overage, reduction=self.reduction)
    
    def convert_cost_param(self, cost_param: Parameter | np.ndarray, input_dtype: torch.dtype = torch.float32, device: torch.device = torch.device('cpu'), target_shape: Tuple = None) -> torch.Tensor:
        
        if isinstance(cost_param, Parameter):
            cost_param =  cost_param.get_value()

        if isinstance(cost_param, np.ndarray):
            cost_param = torch.tensor(cost_param, dtype=input_dtype, device=device)
        elif isinstance(cost_param, torch.Tensor):
            # ensure dtype and device are the same as the input tensor
            cost_param = cost_param.to(dtype=input_dtype, device=device)
        else:
            raise ValueError(f"quantile must be of type Parameter, np.ndarray, or torch.Tensor, but got {type(cost_param)}")

        # check if quantile is of size 1:
        if cost_param.size() == (1,):
            cost_param = cost_param.expand(target_shape)
        elif cost_param.size() != target_shape:
            raise ValueError(f"quantile must be of size 1 or the same size as the target tensor, but got {cost_param.size()} and {target_shape}")

        return cost_param
