"""Soft Actor Critic based agent"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../nbs/51_RL_agents/10_SAC_agents.ipynb.

# %% auto 0
__all__ = ['SACBaseAgent', 'SACAgent', 'SACRNNAgent']

# %% ../../../nbs/51_RL_agents/10_SAC_agents.ipynb 4
import logging

# set logging level to INFO
logging.basicConfig(level=logging.INFO)

from abc import ABC, abstractmethod
from typing import Union, Optional, List, Tuple, Callable, Any
import numpy as np
import os

from ...envs.base import BaseEnvironment
from .mushroom_rl import MushroomBaseAgent
from ...utils import MDPInfo, Parameter, merge_dictionaries
from ...obsprocessors import FlattenTimeDimNumpy
from ...RL_approximators import MLPStateAction, MLPActor, RNNStateAction, RNNActor
from ...postprocessors import ClipAction

from ...dataloaders.base import BaseDataLoader

from mushroom_rl.algorithms.actor_critic.deep_actor_critic import SAC

import torch
import torch.nn.functional as F
from torchinfo import summary
from IPython import get_ipython

from copy import deepcopy

import time

# %% ../../../nbs/51_RL_agents/10_SAC_agents.ipynb 5
class SACBaseAgent(MushroomBaseAgent):

    """
    Base agent for the Soft Actor-Critic (SAC) algorithm. 
    """

    def __init__(self, 
                environment_info: MDPInfo,

                # Not input regarding network architecture --> to be set in subclass

                learning_rate_actor: float = 3e-4,
                learning_rate_critic: float | None = None, # If none, then it is set to learning_rate_actor
                initial_replay_size: int = 64,
                max_replay_size: int = 50000,
                batch_size: int = 64,
                warmup_transitions: int = 100,
                lr_alpha: float = 3e-4,
                tau: float = 0.005,
                log_std_min: float = -20.0,
                log_std_max: float = 2.0,
                use_log_alpha_loss=False,
                target_entropy: float | None = None,
                
                drop_prob: float = 0.0,
                batch_norm: bool = False,
                init_method: str = "xavier_uniform", # "xavier_uniform", "xavier_normal", "he_normal", "he_uniform", "normal", "uniform"

                optimizer: str = "Adam", # "Adam" or "SGD" or "RMSprop"  
                loss: str = "MSE", # currently only MSE is supported     
                obsprocessors: list | None = None,      # default: []
                device: str = "cpu", # "cuda" or "cpu"
                agent_name: str | None = "SAC",

                network_actor_mu_params: dict = None,
                network_actor_sigma_params: dict = None,
                network_critic_params: dict = None,

                ):

        #### To set in the subclass:
        # potential pre-processor
        # input shapes for actor and critic, output shape for actor
        # actor and critic network classes
        # actor and critic network parameters

        use_cuda = self.set_device(device)

        self.warmup_training_steps = initial_replay_size

        OptimizerClass=self.get_optimizer_class(optimizer)
        learning_rate_critic = learning_rate_critic or learning_rate_actor
        lossfunction = self.get_loss_function(loss)

        actor_mu_params = dict(
                                    drop_prob=drop_prob,
                                    batch_norm=batch_norm,
                                    init_method=init_method,

                                    use_cuda=use_cuda,
                                    dropout=self.dropout
        )

        actor_sigma_params = dict(
                                    drop_prob=drop_prob,
                                    batch_norm=batch_norm,
                                    init_method=init_method,

                                    use_cuda=use_cuda,
                                    dropout=self.dropout
        )

        actor_mu_params = merge_dictionaries(actor_mu_params, network_actor_mu_params)
        actor_sigma_params = merge_dictionaries(actor_sigma_params, network_actor_sigma_params)

        actor_optimizer = {'class': OptimizerClass,
            'params': {'lr': learning_rate_actor}} 

        critic_optimizer = {'class': OptimizerClass,
            'params': {'lr': learning_rate_critic}}

        critic_params = dict(
                                optimizer = critic_optimizer,
                                loss=lossfunction,
                                drop_prob=drop_prob,
                                batch_norm=batch_norm,
                                init_method=init_method,

                                use_cuda=use_cuda,
                                dropout=self.dropout,)
                            
        critic_params = merge_dictionaries(critic_params, network_critic_params)

        self.agent = SAC(
            mdp_info=environment_info,
            actor_mu_params=actor_mu_params,
            actor_sigma_params=actor_sigma_params,
            actor_optimizer=actor_optimizer,
            critic_params=critic_params,
            batch_size=batch_size,
            initial_replay_size=initial_replay_size,
            max_replay_size=max_replay_size,
            warmup_transitions=warmup_transitions,
            tau=tau,
            lr_alpha=lr_alpha,
            use_log_alpha_loss=use_log_alpha_loss,
            log_std_min=log_std_min,
            log_std_max=log_std_max,
            target_entropy=target_entropy,
            critic_fit_params=None
        )

        super().__init__(
            environment_info=environment_info,
            obsprocessors=obsprocessors,
            device=device,
            agent_name=agent_name
        )

        batch_dim = 1
        logging.info("Actor network (mu network):")
        if logging.getLogger().isEnabledFor(logging.INFO):
            input_size = self.add_batch_dimension_for_shape(actor_mu_params["input_shape"], batch_dim=batch_dim)
            input_size = self.convert_recursively_to_int(input_size)
            if isinstance(input_size, list):
                input_tensor = torch.randn(1, *actor_mu_params["input_shape"][0]).to(self.device).view(batch_dim, -1)
                if len(input_size) == 2:
                    mlp_features = torch.randn(batch_dim, *actor_mu_params["input_shape"][1]).to(self.device)
                    input_tensor = torch.cat((input_tensor, mlp_features), dim=1)
            else:
                input_tensor = torch.randn(batch_dim, *actor_mu_params["input_shape"]).to(self.device)
            input_tuple = (input_tensor,)
            if get_ipython() is not None:
                print(summary(self.actor, input_data=input_tuple, device=self.device))
            else:
                summary(self.actor, input_data=input_tuple, device=self.device)
            time.sleep(0.2)

        logging.info("################################################################################")
        logging.info("Critic network:")
        if logging.getLogger().isEnabledFor(logging.INFO):
            input_size = self.add_batch_dimension_for_shape(critic_params["input_shape"])
            input_size = self.convert_recursively_to_int(input_size)
            action_sample = torch.randn(batch_dim, *critic_params["input_shape"][1]).to(self.device)
            if isinstance(input_size[0], tuple):
                state_sample = torch.randn(batch_dim, *critic_params["input_shape"][0]).to(self.device)
            else:
                state_sample = torch.randn(batch_dim, *critic_params["input_shape"][0][0]).to(self.device).view(batch_dim, -1)
                if len(input_size[0]) == 2:
                    state_mlp_sample = torch.randn(batch_dim, *critic_params["input_shape"][0][1]).to(self.device)
                    state_sample = torch.cat((state_sample, state_mlp_sample), dim=1)
            input_tuple = (state_sample, action_sample)
            if get_ipython() is not None:
                print(summary(self.critic, input_data=input_tuple, device=self.device))
            else:
                summary(self.critic, input_data=input_tuple, device=self.device)
            # print(summary(self.critic, input_data=input_tuple, device=self.device))

    def get_network_list(self, set_actor_critic_attributes: bool = True):
        """ Get the list of networks in the agent for the save and load functions
        Get the actor for the predict function in eval mode """

        networks = []
        ensemble_critic = self.agent._critic_approximator._impl.model
        for i, model in enumerate(ensemble_critic):
            networks.append(model.network)
        networks.append(self.agent.policy._mu_approximator._impl.model.network)
        networks.append(self.agent.policy._sigma_approximator._impl.model.network)

        actor = self.agent.policy._mu_approximator._impl.model.network
        critic = ensemble_critic[0].network

        if set_actor_critic_attributes:
            return networks, actor, critic
        else:
            return networks

    def predict_(self, observation: np.ndarray) -> np.ndarray: #
        """ Do one forward pass of the model directly and return the prediction.
        Apply tanh as implemented for the SAC actor in mushroom_rl"""
        
        # make observation torch tensor
        device = next(self.actor.parameters()).device
        observation = torch.tensor(observation, dtype=torch.float32).to(device)

        action = self.actor.forward(observation)
        action = torch.tanh(action)
        action = action * self.agent.policy._delta_a + self.agent.policy._central_a
        action = action.cpu().detach().numpy()

        return action

# %% ../../../nbs/51_RL_agents/10_SAC_agents.ipynb 6
class SACAgent(SACBaseAgent):

    """
    XXX
    """

    dropout = True # always keep in True for mushroom_RL, dropout is not desired set drop_prob=0.0

    def __init__(self, 
                environment_info: MDPInfo,

                hidden_layers: List = None, # if None, then default is [64, 64]
                activation: str = "relu", # "relu", "sigmoid", "tanh", "leakyrelu", "elu"

                learning_rate_actor: float = 3e-4,
                learning_rate_critic: float | None = None, # If none, then it is set to learning_rate_actor
                initial_replay_size: int = 64,
                max_replay_size: int = 50000,
                batch_size: int = 64,
                warmup_transitions: int = 100,
                lr_alpha: float = 3e-4,
                tau: float = 0.005,
                log_std_min: float = -20.0,
                log_std_max: float = 2.0,
                use_log_alpha_loss=False,
                target_entropy: float | None = None,

                drop_prob: float = 0.0,
                batch_norm: bool = False,
                init_method: str = "xavier_uniform", # "xavier_uniform", "xavier_normal", "he_normal", "he_uniform", "normal", "uniform"

                optimizer: str = "Adam", # "Adam" or "SGD" or "RMSprop"  
                loss: str = "MSE", # currently only MSE is supported     
                obsprocessors: list | None = None,      # default: []
                device: str = "cpu", # "cuda" or "cpu"
                agent_name: str | None = "SAC",
                observation_space_shape = None, # optional when it cannot be inferred from environment_info (e.g. for dict spaces)
                action_space_shape = None, # optional when it cannot be inferred from environment_info (e.g. for dict spaces)
                ):

        # The standard SAC agent needs a 2D input, so we need to flatten the time dimension
        flatten_time_dim_processor = FlattenTimeDimNumpy(allow_2d=True, batch_dim_included=False)
        obsprocessors = (obsprocessors or []) + [flatten_time_dim_processor]

        # determine observation and action shapes
        obs_space_shape = observation_space_shape or self.get_input_shape(environment_info.observation_space)
        act_space_shape = action_space_shape or environment_info.action_space.shape

        obs_space_shape = self.convert_recursively_to_int(obs_space_shape)
        act_space_shape = self.convert_recursively_to_int(act_space_shape)

        actor_input_shape = obs_space_shape # Note: This can be a list or tuple 
        actor_output_shape = act_space_shape # Note: This can be a list or tuple
        critic_input_shape = [obs_space_shape, act_space_shape,] # Note: This can be a list or tuple

        # Set networks (use classes, not instances)
        actor_mu_network = MLPActor
        actor_sigma_network = MLPActor
        critic_network = MLPStateAction

        # Set default for network architecture
        hidden_layers = hidden_layers or [64, 64]

        # Set network parameters
        network_actor_mu_params = dict(
                                    network = MLPActor,
                                    input_shape=actor_input_shape,
                                    output_shape=actor_output_shape,
                                    hidden_layers=hidden_layers,
                                    activation=activation,
        )

        network_actor_sigma_params = dict(
                                    network = MLPActor,
                                    input_shape=actor_input_shape,
                                    output_shape=actor_output_shape,
                                    hidden_layers=hidden_layers,
                                    activation=activation,
        )

        network_critic_params = dict(
                                    network = MLPStateAction,
                                    input_shape=critic_input_shape,
                                    output_shape=(1,),
                                    hidden_layers=hidden_layers,
                                    activation=activation,
        )

        super().__init__(
            environment_info=environment_info,

            learning_rate_actor=learning_rate_actor,
            learning_rate_critic=learning_rate_critic,
            initial_replay_size=initial_replay_size,
            max_replay_size=max_replay_size,
            batch_size=batch_size,
            warmup_transitions=warmup_transitions,
            lr_alpha=lr_alpha,
            tau=tau,
            log_std_min=log_std_min,
            log_std_max=log_std_max,
            use_log_alpha_loss=use_log_alpha_loss,
            target_entropy=target_entropy,

            drop_prob=drop_prob,
            batch_norm=batch_norm,
            init_method=init_method,

            optimizer=optimizer,
            loss=loss,
            obsprocessors=obsprocessors,
            device=device,
            agent_name=agent_name,

            network_actor_mu_params=network_actor_mu_params,
            network_actor_sigma_params=network_actor_sigma_params,
            network_critic_params=network_critic_params,
        ) 

# %% ../../../nbs/51_RL_agents/10_SAC_agents.ipynb 8
class SACRNNAgent(SACBaseAgent):

    """
    XXX
    """

    dropout = True # always keep in True for mushroom_RL, dropout is not desired set drop_prob=0.0

    def __init__(self, 
                environment_info: MDPInfo,

                hidden_layers_RNN: int = 1, # Initial RNN layers
                num_hidden_units_RNN: int = 64, # Initial number of hidden units in RNN layers
                RNN_cell: str = "GRU", # "LSTM", "GRU", "RNN"
                hidden_layers_MLP: List = None, # MLP layers behind RNN: if None, then default is [64, 64]
                hidden_layers_input_MLP: List = None, # MLP layers for  non-time features. Default is None
                activation: str = "relu", # "relu", "sigmoid", "tanh", "leakyrelu", "elu"

                learning_rate_actor: float = 3e-4,
                learning_rate_critic: float | None = None, # If none, then it is set to learning_rate_actor
                initial_replay_size: int = 64,
                max_replay_size: int = 50000,
                batch_size: int = 64,
                warmup_transitions: int = 100,
                lr_alpha: float = 3e-4,
                tau: float = 0.005,
                log_std_min: float = -20.0,
                log_std_max: float = 2.0,
                use_log_alpha_loss=False,
                target_entropy: float | None = None,

                drop_prob: float = 0.0,
                batch_norm: bool = False,
                init_method: str = "xavier_uniform", # "xavier_uniform", "xavier_normal", "he_normal", "he_uniform", "normal", "uniform"

                optimizer: str = "Adam", # "Adam" or "SGD" or "RMSprop"  
                loss: str = "MSE", # currently only MSE is supported     
                obsprocessors: list | None = None,      # default: []
                device: str = "cpu", # "cuda" or "cpu"
                agent_name: str | None = "SAC",
                observation_space_shape = None, # optional when it cannot be inferred from environment_info (e.g. for dict spaces)
                action_space_shape = None, # optional when it cannot be inferred from environment_info (e.g. for dict spaces)
                ):

        # # The standard SAC agent needs a 2D input, so we need to flatten the time dimension
        # flatten_time_dim_processor = FlattenTimeDimNumpy(allow_2d=True, batch_dim_included=False)
        # obsprocessors = (obsprocessors or []) + [flatten_time_dim_processor]

        # determine observation and action shapes
        obs_space_shape = observation_space_shape or self.get_input_shape(environment_info.observation_space, flatten_time_dim=False)
        act_space_shape = action_space_shape or environment_info.action_space.shape
    
        obs_space_shape = self.convert_recursively_to_int(obs_space_shape)
        act_space_shape = self.convert_recursively_to_int(act_space_shape)

        if isinstance(obs_space_shape, list) and len(obs_space_shape[0]) == 1 or len(obs_space_shape) == 1:
            raise ValueError("The RNN-based SAC needs at least one 2D input (time x features)")


        # determine shapes
        actor_input_shape = obs_space_shape # Note: This can be a list or tuple
        actor_output_shape = act_space_shape # Note: This can be a list or tuple
        
        critic_input_shape = [obs_space_shape, act_space_shape]

        # Determine raw input shape for mushroom to work:
        if isinstance(actor_input_shape, list):
            actor_input_shape_mushroom = actor_input_shape[0][0]*actor_input_shape[0][1] + actor_input_shape[1][0], # if composite space, then flattend vector
            critic_input_shape_mushroom = [actor_input_shape_mushroom, act_space_shape]
        else:
            actor_input_shape_mushroom = actor_input_shape # if only time dimension, then keep 2d input
            critic_input_shape_mushroom = critic_input_shape

        # Set networks (use classes, not instances)
        actor_mu_network = RNNActor
        actor_sigma_network = RNNActor
        critic_network = RNNStateAction

        # Set default for network architecture
        hidden_layers_MLP = hidden_layers_MLP or [64, 64]

        # Set network parameters
        network_actor_mu_params = dict(
                                    network = RNNActor,
                                    input_shape=actor_input_shape_mushroom,
                                    input_shape_=actor_input_shape,
                                    output_shape=actor_output_shape,
                                    hidden_layers_RNN=hidden_layers_RNN,
                                    num_hidden_units_RNN=num_hidden_units_RNN,
                                    hidden_layers_MLP=hidden_layers_MLP,
                                    hidden_layers_input_MLP=hidden_layers_input_MLP,
                                    RNN_cell=RNN_cell,
                                    activation=activation,
        )

        network_actor_sigma_params = dict(
                                    network = RNNActor,
                                    input_shape=actor_input_shape_mushroom,
                                    input_shape_=actor_input_shape,
                                    output_shape=actor_output_shape,
                                    hidden_layers_RNN=hidden_layers_RNN,
                                    num_hidden_units_RNN=num_hidden_units_RNN,
                                    hidden_layers_MLP=hidden_layers_MLP,
                                    hidden_layers_input_MLP=hidden_layers_input_MLP,
                                    RNN_cell=RNN_cell,
                                    activation=activation,
        )

        network_critic_params = dict(
                                    network = RNNStateAction,
                                    input_shape=critic_input_shape_mushroom,
                                    input_shape_=critic_input_shape,
                                    output_shape=(1,),
                                    hidden_layers_RNN=hidden_layers_RNN,
                                    num_hidden_units_RNN=num_hidden_units_RNN,
                                    hidden_layers_MLP=hidden_layers_MLP,
                                    hidden_layers_input_MLP=hidden_layers_input_MLP,
                                    RNN_cell=RNN_cell,
                                    activation=activation,
        )

        super().__init__(
            environment_info=environment_info,

            learning_rate_actor=learning_rate_actor,
            learning_rate_critic=learning_rate_critic,
            initial_replay_size=initial_replay_size,
            max_replay_size=max_replay_size,
            batch_size=batch_size,
            warmup_transitions=warmup_transitions,
            lr_alpha=lr_alpha,
            tau=tau,
            log_std_min=log_std_min,
            log_std_max=log_std_max,
            use_log_alpha_loss=use_log_alpha_loss,
            target_entropy=target_entropy,

            drop_prob=drop_prob,
            batch_norm=batch_norm,
            init_method=init_method,

            optimizer=optimizer,
            loss=loss,
            obsprocessors=obsprocessors,
            device=device,
            agent_name=agent_name,

            network_actor_mu_params=network_actor_mu_params,
            network_actor_sigma_params=network_actor_sigma_params,
            network_critic_params=network_critic_params,
        ) 
