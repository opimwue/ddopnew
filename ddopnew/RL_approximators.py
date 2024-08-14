# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/60_approximators/21_critic_networks.ipynb.

# %% auto 0
__all__ = ['RNNWrapper', 'BaseApproximator', 'BaseApproximatorMLP', 'RNNMLPHybrid', 'BaseApproximatorRNN', 'MLPStateAction',
           'MLPState', 'MLPActor', 'RNNActor', 'RNNStateAction']

# %% ../nbs/60_approximators/21_critic_networks.ipynb 4
from abc import ABC, abstractmethod
from typing import Union, Tuple, List
import numpy as np

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

import time

# %% ../nbs/60_approximators/21_critic_networks.ipynb 5
class RNNWrapper(nn.Module):
    def __init__(self, rnn_cell_class, *args, **kwargs):
        """
        Initializes the RNNWrapper with the specified RNN cell.
        
        Parameters:
        - rnn_cell_class: The RNN cell class (e.g., nn.GRU, nn.LSTM, nn.RNN).
        - *args, **kwargs: The arguments and keyword arguments to be passed to the RNN cell.
        """
        super(RNNWrapper, self).__init__()
        self.rnn = rnn_cell_class(*args, **kwargs)

    def forward(self, x):
        output, _ = self.rnn(x)  # Extract and return only the output
        return output

    @classmethod
    def create(cls, rnn_cell_class):
        """
        A factory method to create a new RNNWrapper subclass with a specific RNN cell.
        
        Parameters:
        - rnn_cell_class: The RNN cell class to be wrapped (e.g., nn.GRU, nn.LSTM).
        
        Returns:
        - A new subclass of RNNWrapper.
        """
        class SpecificRNNWrapper(cls):
            def __init__(self, *args, **kwargs):
                super(SpecificRNNWrapper, self).__init__(rnn_cell_class, *args, **kwargs)

        return SpecificRNNWrapper

# %% ../nbs/60_approximators/21_critic_networks.ipynb 6
class BaseApproximator():

    """ Some basic functions for approximators """

    def __init__(self):
        super().__init__()

    def init_weights(self, layer, init_method, activation):
        """ Initialize the weights of a layer """
        init_method_function = self.select_init_method(init_method)
        
        # Check if initialization method requires gain
        if init_method in ["xavier_uniform", "xavier_normal"]:
            if activation == "identity":
                activation = "linear"
            gain = nn.init.calculate_gain(activation)
            init_method_function(layer.weight, gain=gain)
        else:
            init_method_function(layer.weight)
            
    def init_rnn_weights(self, rnn_layer, init_method):
        """Initialize the weights for the RNN layer."""
        init_method_function = self.select_init_method(init_method)

        for name, param in rnn_layer.named_parameters():
            if 'weight' in name:
                # Initialize weights using the selected method
                init_method_function(param)
            elif 'bias' in name:
                # Initialize biases to zero
                nn.init.constant_(param, 0)
                
    @staticmethod
    def select_rnn_cell(RNN_cell):
        """ Select the RNN cell based on input string """
        RNN_cell = RNN_cell.lower()  # Convert input to lowercase for consistency
        if RNN_cell == "gru":
            rnn_cell_class = nn.GRU
        elif RNN_cell == "lstm":
            rnn_cell_class = nn.LSTM
        elif RNN_cell == "rnn":
            rnn_cell_class = nn.RNN
        else:
            raise ValueError(f"RNN cell '{RNN_cell}' not recognized")

        return RNNWrapper.create(rnn_cell_class)

    @staticmethod
    def select_init_method(init_method):
        """ Select the initialization method based on input string """
        init_method = init_method.lower()
        if init_method in ["xavier_uniform", "xavier"]:
            return nn.init.xavier_uniform_
        elif init_method in ["xavier_normal", "xaviernorm"]:
            return nn.init.xavier_normal_
        elif init_method in ["he_uniform", "kaiming_uniform"]:
            return nn.init.kaiming_uniform_
        elif init_method in ["he_normal", "kaiming_normal"]:
            return nn.init.kaiming_normal_
        elif init_method in ["normal", "gaussian"]:
            return nn.init.normal_
        elif init_method == "uniform":
            return nn.init.uniform_
        else:
            raise ValueError("Initialization method not recognized")

    @staticmethod
    def select_activation(activation):
        """ Select the activation function based on input string """
        activation = activation.lower()  # Convert input to lowercase for consistency
        if activation == "relu":
            return nn.ReLU
        elif activation == "sigmoid":
            return nn.Sigmoid
        elif activation == "tanh":
            return nn.Tanh
        elif activation == "elu":
            return nn.ELU
        elif activation == "leakyrelu":
            return nn.LeakyReLU
        elif activation == "identity":
            return nn.Identity
        else:
            raise ValueError(f"Activation function {activation} not recognized")

    def forward(self, x):
        """ Forward pass through the network - overwrite this if necessary """
        return self.model(x)

# %% ../nbs/60_approximators/21_critic_networks.ipynb 7
class BaseApproximatorMLP(BaseApproximator, nn.Module):

    """ Some basic functions for approximators """

    def __init__(self):
        super().__init__()
    
    def build_MLP(  self,
                    input_size: int,
                    output_size: int,
                    hidden_layers: list,
                    activation: str = "relu",
                    drop_prob: float = 0.0,
                    batch_norm: bool = False,
                    final_activation: str = "identity",
                    init_method: str = "xavier_uniform" # Parameter for initialization
                  ):

        """ Builds a multi-layer perceptron (MLP) """

        HiddenActivation = self.select_activation(activation)
        FinalActivation = self.select_activation(final_activation)

        layers = []

        # Hidden layers
        last_size = input_size
        for num_neurons in hidden_layers:
            
            linear_layer = nn.Linear(last_size, num_neurons)
            self.init_weights(linear_layer, init_method, activation)
            layers.append(linear_layer)

            if batch_norm:
                layers.append(nn.BatchNorm1d(num_neurons))
        
            layers.append(HiddenActivation())
            layers.append(nn.Dropout(p=drop_prob))

            last_size = num_neurons
        
        # Output layer
        output_layer = nn.Linear(last_size, output_size)
        self.init_weights(output_layer, init_method, final_activation)
        layers.append(output_layer)
        layers.append(FinalActivation())

        # Combine layers
        model = nn.Sequential(*layers)

        self.model = model

# %% ../nbs/60_approximators/21_critic_networks.ipynb 8
class RNNMLPHybrid(nn.Module, BaseApproximator):

    """ A hybrid model combining an RNN and an MLP """

    def __init__(self, 
                 RNN_input_size: int,
                 MLP_input_size: int | None,
                 output_size: int,
                 num_hidden_units_RNN: int,
                 hidden_layers_RNN: int,
                 hidden_layers_MLP: List[int],
                 hidden_layers_input_MLP: List[int] | None,
                 RNN_cell: nn.Module,
                 activation: nn.Module,
                 final_activation: nn.Module,
                 drop_prob: float,
                 batch_norm: bool,
                 init_method: str):
        super(RNNMLPHybrid, self).__init__()

        HiddenActivation = self.select_activation(activation)
        FinalActivation = self.select_activation(final_activation)
        RNNCell = self.select_rnn_cell(RNN_cell)

        # RNN
        # RNN layers

        rnn_layers = []
        rnn = RNNCell(RNN_input_size, num_hidden_units_RNN, hidden_layers_RNN, batch_first=True, dropout=drop_prob)
        self.init_rnn_weights(rnn, init_method)
        hidden_activation_rnn = HiddenActivation()  # Activation used after RNN layers
        rnn_layers.append(rnn)
        rnn_layers.append(hidden_activation_rnn)

        self.rnn = nn.Sequential(*rnn_layers)

        # Input MLP, if required:
        last_size = 0 if MLP_input_size is None else MLP_input_size
        if hidden_layers_input_MLP is not None:

            if last_size == 0:
                raise ValueError("MLP input size must be specified if input MLP is used")
            
            layers_input_MLP = []
            for num_neurons in hidden_layers_input_MLP:
                linear_layer = nn.Linear(last_size, num_neurons)
                self.init_weights(linear_layer, init_method, activation)
                layers_input_MLP.append(linear_layer)
                if batch_norm:
                    layers_input_MLP.append(nn.BatchNorm1d(num_neurons))
                layers_input_MLP.append(HiddenActivation())
                layers_input_MLP.append(nn.Dropout(p=drop_prob))
                last_size = num_neurons
            
            self.input_mlp = nn.Sequential(*layers_input_MLP)
        else:
            self.input_mlp = None
        
        # Main MLP layers
        layers_MLP = []
        last_size = num_hidden_units_RNN + last_size
        for num_neurons in hidden_layers_MLP:
            linear_layer = nn.Linear(last_size, num_neurons)
            self.init_weights(linear_layer, init_method, activation)
            layers_MLP.append(linear_layer)
            if batch_norm:
                layers_MLP.append(nn.BatchNorm1d(num_neurons))
            layers_MLP.append(HiddenActivation())
            layers_MLP.append(nn.Dropout(p=drop_prob))
            last_size = num_neurons

        # Output layer
        output_layer = nn.Linear(last_size, output_size)
        self.init_weights(output_layer, init_method, final_activation)
        layers_MLP.append(output_layer)

        self.main_mlp = nn.Sequential(*layers_MLP)

    
    def forward(self, x_rnn, x_mlp=None):
        # RNN

        rnn_out = self.rnn(x_rnn) # Only one output due to the wrapper
        rnn_out = rnn_out[:, -1, :]  # Take the last output of the RNN
        
        # Input MLP
        if x_mlp is not None:
            if self.input_mlp is not  None:
                x_mlp = self.input_mlp(x_mlp)
            x = torch.cat((rnn_out, x_mlp), dim=1)
        else:
            x = rnn_out

        # Main MLP
        x = self.main_mlp(x)

        return x

# %% ../nbs/60_approximators/21_critic_networks.ipynb 9
class BaseApproximatorRNN(BaseApproximator, nn.Module):

    """ Some basic functions for approximators """

    def __init__(self):
        super().__init__()

    def build_RNN(  self,
                    input_size: int | List[int], # is List, it means that multiple inputs are used. The first element is alwas for the RNN, the rest for the MLP
                    output_size: int,
                    hidden_layers_RNN:int,
                    num_hidden_units_RNN: int,
                    hidden_layers_MLP:List,
                    hidden_layers_input_MLP: List | None = None, # If a separate MLP is used for (potential) MLP input
                    RNN_cell: str = "GRU",
                    activation: str = "relu",
                    drop_prob: float = 0.0,
                    batch_norm: bool = False,
                    final_activation: str = "identity",
                    init_method: str = "xavier_uniform" # Parameter for initialization
                  ):

        """ Builds a recurrent neural network (RNN) """

        if isinstance(input_size, int):
            RNN_input_size = input_size
            MLP_input_size = None
        elif isinstance(input_size, list):

            if len(input_size) != 2:
                raise ValueError(f"Input size must be a list of length 2 (got {len(input_size)}) with elementes (RNN_input_size, MLP_input_size)")

            RNN_input_size = input_size[0]
            MLP_input_size = input_size[1]

        else:
            raise ValueError("Input size must be an integer or a list of integers")
    
        self.model = RNNMLPHybrid(  RNN_input_size,
                                    MLP_input_size,
                                    output_size,
                                    num_hidden_units_RNN,
                                    hidden_layers_RNN,
                                    hidden_layers_MLP,
                                    hidden_layers_input_MLP,
                                    RNN_cell,
                                    activation,
                                    final_activation,
                                    drop_prob,
                                    batch_norm,
                                    init_method,
                                    )


        

# %% ../nbs/60_approximators/21_critic_networks.ipynb 10
class MLPStateAction(BaseApproximatorMLP):

    """Multilayer perceptron model for critic networks that take
    both states and actions as inputs to output the q-value"""

    def __init__(self,
                    input_shape: Tuple | List[Tuple], # number of features
                    output_shape: Tuple, # number of outputs/actions
                    hidden_layers: list, # list of number of neurons in each hidden layer
                    activation: str = "relu",
                    drop_prob: float = 0.0, # dropout probability
                    batch_norm: bool = False, # whether to apply batch normalization
                    final_activation: str = "identity", # whether to apply ReLU activation to the output
                    init_method: str = "xavier_uniform",  # Parameter for initialization
                    use_cuda: bool = False, # handled by mushroomRL, not used here
                    dropout: bool = False # legacy parameter to ensure compatibility, use drop_prob instead
                    ):

        super().__init__()

        # if input shape is list, then concatenate the elements
        if isinstance(input_shape, list):
            input_shape = (sum([shape[0] for shape in input_shape]),)
        
        self.build_MLP(    input_shape[0],
                            output_shape[0],
                            hidden_layers,
                            activation, 
                            drop_prob,
                            batch_norm,
                            final_activation,
                            init_method)

    def forward(self, state, action):


        state_action = torch.cat([state.float(), action.float()], dim=1)

        q = self.model(state_action)

        # TODO: check if squeeze is necessary
        # return q
        return torch.squeeze(q)

# %% ../nbs/60_approximators/21_critic_networks.ipynb 11
class MLPState(BaseApproximatorMLP):

    """Multilayer perceptron model for critic networks that take
    both states and actions as inputs to output the q-value"""

    def __init__(self,
                    input_shape: Tuple, # number of features
                    output_shape: Tuple, # number of outputs/actions
                    hidden_layers: list, # list of number of neurons in each hidden layer
                    activation: str = "relu",
                    drop_prob: float = 0.0, # dropout probability
                    batch_norm: bool = False, # whether to apply batch normalization
                    final_activation: str = "identity", # whether to apply ReLU activation to the output
                    init_method: str = "xavier_uniform",  # Parameter for initialization
                    use_cuda: bool = False, # handled by mushroomRL, not used here
                    dropout: bool = False # legacy parameter to ensure compatibility, use drop_prob instead
                    ):

        super().__init__()
        
        self.build_MLP(    input_shape[0],
                            output_shape[0],
                            hidden_layers,
                            activation, 
                            drop_prob,
                            batch_norm,
                            final_activation,
                            init_method)

    def forward(self, state):

        state = state.float()

        q = self.model(state)

        # TODO: check if squeeze is necessary
        # return q.squeeze()
        return q

# %% ../nbs/60_approximators/21_critic_networks.ipynb 12
class MLPActor(BaseApproximatorMLP):

    """Multilayer perceptron model for critic networks that take
    both states and actions as inputs to output the q-value"""

    def __init__(self,
                    input_shape: Tuple, # number of features
                    output_shape: Tuple, # number of outputs/actions
                    hidden_layers: list, # list of number of neurons in each hidden layer
                    activation: str = "relu",
                    drop_prob: float = 0.0, # dropout probability
                    batch_norm: bool = False, # whether to apply batch normalization
                    final_activation: str = "identity", # whether to apply ReLU activation to the output
                    init_method: str = "xavier_uniform",  # Parameter for initialization
                    use_cuda: bool = False,
                    dropout: bool = False, # legacy parameter to ensure compatibility, use drop_prob instead
                    **kwargs
                    ): 

        super().__init__()
        
        self.build_MLP(    input_shape[0],
                            output_shape[0],
                            hidden_layers,
                            activation, 
                            drop_prob,
                            batch_norm,
                            final_activation,
                            init_method)

    def forward(self, state):

        state = state.float()

        a = self.model(state)

        return a

# %% ../nbs/60_approximators/21_critic_networks.ipynb 13
class RNNActor(BaseApproximatorRNN):

    """Multilayer perceptron model for critic networks that take
    both states and actions as inputs to output the q-value"""

    def __init__(self,
                    input_shape: Tuple | List[Tuple], # number of features
                    output_shape: Tuple, # number of outputs/actions
                    hidden_layers_RNN: int, # number of initial hidden RNN layers
                    num_hidden_units_RNN: int, # number of neurons in the RNN layers
                    hidden_layers_MLP: List, # list of number of neurons in each hidden MLP layer, following the RNN layers
                    hidden_layers_input_MLP: List | None = None, # If a separate MLP is used for (potential) MLP input
                    RNN_cell: str = "GRU", # RNN cell type
                    activation: str = "relu",
                    drop_prob: float = 0.0, # dropout probability
                    batch_norm: bool = False, # whether to apply batch normalization
                    final_activation: str = "identity", # whether to apply ReLU activation to the output
                    init_method: str = "xavier_uniform",  # Parameter for initialization
                    use_cuda: bool = False,
                    dropout: bool = False, # legacy parameter to ensure compatibility, use drop_prob instead
                    **kwargs
                    ): 

        super().__init__()

        if isinstance(input_shape, tuple):
            if len(input_shape) != 2:
                raise ValueError(f"Input shape must be a tuple with dimensions (time_steps, features), got {input_shape}")
            input_size = input_shape[1]
        else:
            if len(input_shape) > 2:
                raise ValueError(f"Input shape must be a tuple or a list of tuples with length 1 or 2, got length {len(input_shape)}")
            input_size = [input_shape[0][1], input_shape[1][0]]

        self.build_RNN(     input_size,
                            output_shape[0],
                            hidden_layers_RNN,
                            num_hidden_units_RNN,
                            hidden_layers_MLP,
                            hidden_layers_input_MLP,
                            RNN_cell,
                            activation, 
                            drop_prob,
                            batch_norm,
                            final_activation,
                            init_method)

    def forward(self, state):

        state = state.float()

        a = self.model(state)

        return a

# %% ../nbs/60_approximators/21_critic_networks.ipynb 14
class RNNStateAction(BaseApproximatorRNN):

    """Multilayer perceptron model for critic networks that take
    both states and actions as inputs to output the q-value"""

    def __init__(self,
                    input_shape: List[Tuple], # input shape of features for rnn (optional for mlp) and action
                    output_shape: Tuple, # Output shape
                    hidden_layers_RNN: int, # number of initial hidden RNN layers
                    num_hidden_units_RNN: int, # number of neurons in the RNN layers
                    hidden_layers_MLP: List, # list of number of neurons in each hidden MLP layer, following the RNN layers
                    hidden_layers_input_MLP: List | None = None, # structure of MLP to speratly process non-RNN input
                    RNN_cell: str = "GRU", # RNN cell type
                    activation: str = "relu",
                    drop_prob: float = 0.0, # dropout probability
                    batch_norm: bool = False, # whether to apply batch normalization
                    final_activation: str = "identity", # whether to apply ReLU activation to the output
                    init_method: str = "xavier_uniform",  # Parameter for initialization
                    use_cuda: bool = False,
                    dropout: bool = False, # legacy parameter to ensure compatibility, use drop_prob instead
                    **kwargs
                    ): 

        super().__init__()

        # check that input lenght of list is 2 or 3
        if len(input_shape) < 2 or len(input_shape) > 3:
            raise ValueError(f"Input shape must be a list of length 2 or 3, got {len(input_shape)}")
        
        rnn_input = input_shape[0][1] # RNN input is always the first element, only the feature dimension is used
        mlp_input = input_shape[1][0] if len(input_shape) == 2 else input_shape[1][0] + input_shape[2][0] # if there is a separate MLP input, it is the second element
        
        self.build_RNN(     [rnn_input, mlp_input],
                            output_shape[0],
                            hidden_layers_RNN,
                            num_hidden_units_RNN,
                            hidden_layers_MLP,
                            hidden_layers_input_MLP,
                            RNN_cell,
                            activation, 
                            drop_prob,
                            batch_norm,
                            final_activation,
                            init_method)

    def forward(self, state, action):

        if isinstance(state, list):
            rnn_input = state[0]
            non_time_features = state[1]
            mlp_input = torch.cat([non_time_features, action], dim=-1)
        else:
            rnn_input = state
            mlp_input = action

        a = self.model(rnn_input.float(), mlp_input.float())

        return a
