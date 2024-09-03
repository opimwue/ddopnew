"""Base class for dataloaders"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/10_dataloaders/10_base_dataloader.ipynb.

# %% auto 0
__all__ = ['BaseDataLoader']

# %% ../../nbs/10_dataloaders/10_base_dataloader.ipynb 3
import numpy as np
from abc import ABC, abstractmethod
from typing import Union

# %% ../../nbs/10_dataloaders/10_base_dataloader.ipynb 4
class BaseDataLoader(ABC):
   
    """
    Base class for data loaders.
    The idea of the data loader is to provide all external information to the environment
    (including lagged data, demand etc.). Internal data influenced by past decisions (like
    inventory levels) is to be added from within the environment
    """

    def __init__(self):
        self.dataset_type = "train"

    @abstractmethod
    def __len__(self):
        '''
        Returns the length of the dataset. For dataloaders based on distributions, this 
        should return an error that the length is not defined, otherwise it should return
        the number of samples in the dataset.
        '''
        pass

    @abstractmethod   
    def __getitem__(self, idx):

        """
        Returns always a tuple of X and Y data. If no X data is available, return None.
        """
        pass

    @property
    @abstractmethod
    def X_shape(self):
        """
        Returns the shape of the X data.
        It should follow the format (n_samples, n_features). If the data has a time dimension with
        a fixed length, the shape should be (n_samples, n_time_steps, n_features). If the data is 
        generated from a distribtition, n_samples should be set to 1.
        """
        pass

    @property
    @abstractmethod
    def Y_shape(self):
        """
        Returns the shape of the Y data.
        It should follow the format (n_samples, n_SKUs). If the variable of interst is only a single
        SKU, the shape should be (n_samples, 1). If the data is 
        generated from a distribtition, n_samples should be set to 1.
        """
        pass

    @abstractmethod   
    def get_all_X(self,
                dataset_type: str = 'train' # can be 'train', 'val', 'test', 'all'
                ): 

        """
        Returns the entire features dataset. If no X data is available, return None.
        Return either the train, val, test, or all data.
        """
        pass    

    @abstractmethod   
    def get_all_Y(self,
                dataset_type: str = 'train' # can be 'train', 'val', 'test', 'all'
                ): 

        """
        Returns the entire target dataset. If no Y data is available, return None.
        Return either the train, val, test, or all data.
        """
        pass  

    @property
    @abstractmethod   
    def len_train(self):

        """
        Returns the length of the training set. For dataloaders based on distributions, this
        should return an error that the length is not defined, otherwise it should return
        the number of samples in the training set.
        """

        pass

    @property
    @abstractmethod 
    def len_val(self):

        """

        Returns the length of the validation set. For dataloaders based on distributions, this
        should return an error that the length is not defined, otherwise it should return
        the number of samples in the validation set.

        If no valiation set is defined, raise an error.
        """

        pass
    
    @property
    @abstractmethod 
    def len_test(self):
        
        """

        Returns the length of the test set. For dataloaders based on distributions, this
        should return an error that the length is not defined, otherwise it should return
        the number of samples in the test set.

        If no test set is defined, raise an error.
        """

        pass

        
    def train(self):

        """
        Set the internal state of the dataloader to train
        """

        self.dataset_type = "train"

    def val(self):

        """
        Set the internal state of the dataloader to validation
        """

        if self.val_index_start is None:
            raise ValueError('no validation set defined')
        else:
            self.dataset_type = "val"

    def test(self):

        """
        Set the internal state of the dataloader to test
        """

        if self.test_index_start is None:
            raise ValueError('no test set defined')
        else:
            self.dataset_type = "test"

