# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/10_dataloaders/12_tabular_dataloaders.ipynb.

# %% auto 0
__all__ = ['XYDataLoader']

# %% ../../nbs/10_dataloaders/12_tabular_dataloaders.ipynb 3
import numpy as np
from abc import ABC, abstractmethod
from typing import Union

from .base import BaseDataLoader

from sklearn.preprocessing import StandardScaler

# %% ../../nbs/10_dataloaders/12_tabular_dataloaders.ipynb 4
class XYDataLoader(BaseDataLoader):

    """

    A class for datasets with the typicall X, Y structure. Both X
    and Y are numpy arrays. X may be of shape (datapoints, features) or (datapoints, sequence_length, features) 
    if lag features are used. The prep_lag_features can be used to create those lag features. Y is of shape
    (datapoints, units).

    """
    
    def __init__(self,
        X: np.ndarray,
        Y: np.ndarray,
        val_index_start: Union[int, None] = None, 
        test_index_start: Union[int, None] = None, 
        lag_window_params: Union[dict] = None, # default: {'lag_window': 0, 'include_y': False, 'pre_calc': False}
        normalize_features: Union[dict] = None, # default: {'normalize': True, 'ignore_one_hot': True}
    ):

        self.X = X
        self.Y = Y

        self.val_index_start = val_index_start
        self.test_index_start = test_index_start

        # train index ends either at the start of the validation set, the start of the test set or at the end of the dataset
        if self.val_index_start is not None:
            self.train_index_end = self.val_index_start-1
        elif self.test_index_start is not None:
            self.train_index_end = self.test_index_start-1
        else:
            self.train_index_end = len(Y)-1

        self.dataset_type = "train"

        normalize_features = normalize_features or {'normalize': True, 'ignore_one_hot': True}
        lag_window_params = lag_window_params or {'lag_window': 0, 'include_y': False, 'pre_calc': False}

        self.normalize_features(**normalize_features, initial_normalization=True)
        self.prep_lag_features(**lag_window_params)

        # X must at least have datapoint and feature dimension
        if len(X.shape) == 1:
            self.X = X.reshape(-1, 1)
        
        # Y must have at least datapoint and unit dimension (even if only one unit is present)
        if len(Y.shape) == 1:
            self.Y = Y.reshape(-1, 1)

        assert len(X) == len(Y), 'X and Y must have the same length'

        self.num_units = Y.shape[1] # shape 0 is alsways time, shape 1 is the number of units (e.g., SKUs)

        super().__init__()

    def normalize_features(self,
        normalize: bool = True,
        ignore_one_hot: bool = True,
        initial_normalization=False # Flag if it is set before having added lag features
        ):

        """
        Normalize features using a standard scaler. If ignore_one_hot is true, one-hot encoded features are not normalized.

        """

        if normalize:

            scaler = StandardScaler()

            if initial_normalization:

                if len(self.X.shape) == 3:
                    raise ValueError('Normalization not possible with lag features. Please set initial_normalization=False')
            
                scaler.fit(self.X[:self.train_index_end+1]) # +1 to include the last training point
                scaler.transform(self.X)

                if initial_normalization:
                    return
                else:
                    raise NotImplementedError('Normalization after lag features have been set not implemented yet')

                    # Idea:
                        # remove time dimension
                        # normalize features
                        # add time_dimension back
                    # Problem:
                        # usage of prep_lag_features needs to ensure y is not added a second time

    def prep_lag_features(self,
        lag_window: int = 0, # length of the lage window
        include_y: bool = False, # if lag demand shall be included as feature
        pre_calc: bool = False # if all lags are pre-calculated for the entire dataset
        ):

        """
        Create lag feature for the dataset. If "inlcude_y" is true, then a lag-1 of of the target variable is added as a feature.
        If lag-window is > 0, the lag features are added as middle dimension to X. Note that this, e.g., means that with a lag
        window of 1, the data will include 2 time steps, the current features including lag-1 demand and the lag-1 features
        including lag-2 demand. If pre-calc is true, all these calculations are performed on the entire dataset reduce
        computation time later on at the expense of increases memory usage. 

        """
        # to be discussed: Do we need option to only provide lag demand wihtout lag features?
        self.lag_window = lag_window
        self.pre_calc = pre_calc
        self.include_y = include_y
        
        if self.pre_calc:
            if self.include_y:
                # add additional column to X with demand shifted by 1
                self.X = np.concatenate((self.X, np.roll(self.Y, 1, axis=0)), axis=1)
                self.X = self.X[1:] # remove first row
                self.Y = self.Y[1:] # remove first row
                
                self.val_index_start = self.val_index_start-1
                self.test_index_start = self.test_index_start-1
                self.train_index_end  = self.train_index_end-1
        
            if self.lag_window is not None and self.lag_window > 0:

                # add lag features as dimention 2 to X (making it dimension (datapoints, sequence_length, features))
                X_lag = np.zeros((self.X.shape[0], self.lag_window+1, self.X.shape[1]))
                for i in range(self.lag_window+1):
                    if i == 0:
                        features = self.X
                    else:    
                        features = self.X[:-i, :]
                    X_lag[i:, self.lag_window-i, :] = features
                self.X = X_lag[self.lag_window:]
                self.Y = self.Y[self.lag_window:]

                self.val_index_start = self.val_index_start-self.lag_window
                self.test_index_start = self.test_index_start-self.lag_window
                self.train_index_end  = self.train_index_end-self.lag_window

        else:
            self.lag_window = None
            self.include_y = False
            # add time dimension to X

    def update_lag_features(self,
        lag_window: int,
        ):

        """ Update lag window parameters for dataloader object that is already initialized """

        raise NotImplementedError('Not implemented yet')

        # Problem: updating lag_features naively would shorten the dataset each time it is called

    def __getitem__(self, idx): 

        """ get item by index, depending on the dataset type (train, val, test)"""

        if self.dataset_type == "train":
            if idx > self.train_index_end:
                raise IndexError(f'index {idx} out of range{self.train_index_end}')
            idx = idx

        elif self.dataset_type == "val":
            idx = idx + self.val_index_start
            
            if idx >= self.test_index_start:
                raise IndexError(f'index{idx} out of range{self.test_index_start}')
            
        elif self.dataset_type == "test":
            idx = idx + self.test_index_start
            
            if idx >= len(self.X):
                raise IndexError(f'index{idx} out of range{len(self.X)}')
        
        else:
            raise ValueError('dataset_type not set')

        return self.X[idx], self.Y[idx]

    def __len__(self):
        return len(self.X)
    
    @property
    def X_shape(self):
        return self.X.shape
    
    @property
    def Y_shape(self):
        return self.Y.shape

    @property
    def len_train(self):
        return self.train_index_end+1

    @property
    def len_val(self):
        if self.val_index_start is None:
            raise ValueError('no validation set defined')
        return self.test_index_start-self.val_index_start

    @property
    def len_test(self):
        if self.test_index_start is None:
            raise ValueError('no test set defined')
        return len(self.Y)-self.test_index_start

    def get_all_X(self,
                dataset_type: str = 'train' # can be 'train', 'val', 'test', 'all'
                ): 

        """
        Returns the entire features dataset.
        Return either the train, val, test, or all data.
        """

        if dataset_type == 'train':
            return self.X[:self.val_index_start].copy() if self.X is not None else None
        elif dataset_type == 'val':
            return self.X[self.val_index_start:self.test_index_start].copy() if self.X is not None else None
        elif dataset_type == 'test':
            return self.X[self.test_index_start:].copy() if self.X is not None else None
        elif dataset_type == 'all':
            return self.X.copy() if self.X is not None else None
        else:
            raise ValueError('dataset_type not recognized')

    def get_all_Y(self,
                dataset_type: str = 'train' # can be 'train', 'val', 'test', 'all'
                ): 

        """
        Returns the entire target dataset.
        Return either the train, val, test, or all data.
        """

        if dataset_type == 'train':
            return self.Y[:self.val_index_start].copy() if self.Y is not None else None
        elif dataset_type == 'val':
            return self.Y[self.val_index_start:self.test_index_start].copy() if self.Y is not None else None
        elif dataset_type == 'test':
            return self.Y[self.test_index_start:].copy() if self.Y is not None else None
        elif dataset_type == 'all':
            return self.Y.copy() if self.Y is not None else None
        else:
            raise ValueError('dataset_type not recognized')
        
