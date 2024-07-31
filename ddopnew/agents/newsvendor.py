# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/41_NV_agents/10_NV_agents.ipynb.

# %% auto 0
__all__ = ['NewsvendorSAAagent', 'BaseWeightedAgent', 'NewsvendorRFwSAAagent']

# %% ../../nbs/41_NV_agents/10_NV_agents.ipynb 4
from abc import ABC, abstractmethod
from typing import Union
import numpy as np

from ..envs.base import BaseEnvironment

from .base import BaseSAAagent

from sklearn.ensemble import RandomForestRegressor


# %% ../../nbs/41_NV_agents/10_NV_agents.ipynb 5
class NewsvendorSAAagent(BaseSAAagent):

    def __init__(self, environment_info, cu, co):
        self.cu = cu
        self.co = co

        self.sl = cu / (cu + co)

        self.quantiles = np.array([0])

        super().__init__(environment_info)

    def fit(self, X, Y):
        
        # # potential line:
        # X, y = self._validate_data(X, y, multi_output=True)

        weights = np.ones(Y.shape)/Y.shape[0]
        weightPosIndices = np.arange(Y.shape[0])
        
        self.quantiles = self.find_weighted_quantiles(weights, weightPosIndices, self.sl, Y)

    def draw_action(self, observation):
        return self.quantiles

# %% ../../nbs/41_NV_agents/10_NV_agents.ipynb 6
class BaseWeightedAgent(BaseSAAagent):

    def __init__(self, environment_info, cu, co):
        self.cu = cu
        self.co = co

        self.sl = cu / (cu + co)

        super().__init__(environment_info)

        self.fitted = False

    def fit(self, X, Y):
        
        # # potential line:
        # X, y = self._validate_data(X, y, multi_output=True)

        print(X.shape)

        X = self.flatten_X(X) # remove time dimension, if there

        print(X.shape)

        if len(Y.shape) == 2 and Y.shape[1] == 1:
            Y = Y.flatten() 

        self._get_fitted_model(X, Y)

        if Y.ndim == 1:
            Y = np.reshape(Y, (-1, 1))

        # Training data
        self.Y_ = Y
        self.X_ = X
        self.n_samples_ = Y.shape[0]

        # Determine output settings
        self.n_outputs_ = Y.shape[1]
        self.n_features_ = X.shape[1]

        self.fitted=True

    def draw_action(self, observation):

        if self.fitted == False:
            return np.array([0.0])
            
        
        observation = observation.reshape(1, -1)

        observation = self.flatten_X(observation) # remove time dimension, if any

        return self.predict(observation)
    
    @abstractmethod
    def _get_fitted_model(self, X, y):
        """Initialise the underlying model"""

    @abstractmethod
    def _calc_weights(self, sample):
        """Calculate the sample weights"""

    def predict(self, X):
        """Predict value for X.

        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            The input samples to predict.

        Returns
        ----------
        y : array-like of shape (n_samples, n_outputs)
            The predicted values
        """

        X = self._validate_X_predict(X)   
       
        weightsDataList = [self._calc_weights(row) for row in X]
        pred = [self.find_weighted_quantiles(weights, weightPosIndices, self.sl, self.Y_) 
                for weights, weightPosIndices in weightsDataList]
        pred = np.array(pred)        
        
        return pred

# %% ../../nbs/41_NV_agents/10_NV_agents.ipynb 7
class NewsvendorRFwSAAagent(BaseWeightedAgent):

    def __init__(self,
                environment_info,
                cu,
                co,
                n_estimators=100,
                criterion="squared_error",
                max_depth=None,
                min_samples_split=2,
                min_samples_leaf=1,
                min_weight_fraction_leaf=0.0,
                max_features=1.0,
                max_leaf_nodes=None,
                min_impurity_decrease=0.0,
                bootstrap=True,
                oob_score=False,
                n_jobs=None,
                random_state=None,
                verbose=0,
                warm_start=False,
                ccp_alpha=0.0,
                max_samples=None,
                monotonic_cst=None
                ):
        self.criterion = criterion
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.min_weight_fraction_leaf = min_weight_fraction_leaf
        self.max_features = max_features
        self.max_leaf_nodes = max_leaf_nodes
        self.min_impurity_decrease = min_impurity_decrease
        self.bootstrap = bootstrap
        self.oob_score = oob_score
        self.n_jobs = n_jobs
        self.random_state = random_state
        self.verbose = verbose
        self.warm_start = warm_start
        self.ccp_alpha = ccp_alpha
        self.max_samples = max_samples
        self.monotonic_cst = monotonic_cst
        self.weight_function = "w1"

        super().__init__(environment_info, cu, co)

    def _get_fitted_model(self, X, y):
        model = RandomForestRegressor(
            criterion=self.criterion,
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            min_samples_leaf=self.min_samples_leaf,
            min_weight_fraction_leaf=self.min_weight_fraction_leaf,
            max_features=self.max_features,
            max_leaf_nodes=self.max_leaf_nodes,
            min_impurity_decrease=self.min_impurity_decrease,
            bootstrap=self.bootstrap,
            oob_score=self.oob_score,
            n_jobs=self.n_jobs,
            random_state=self.random_state,
            verbose=self.verbose,
            warm_start=self.warm_start,
            ccp_alpha=self.ccp_alpha,
            max_samples=self.max_samples,
            monotonic_cst = self.monotonic_cst
        )

        self.model_ = model.fit(X, y)
        self.train_leaf_indices_ = model.apply(X)

    def _calc_weights(self, sample):
        sample_leaf_indices = self.model_.apply([sample])
        if self.weight_function == "w1":
            n = np.sum(sample_leaf_indices == self.train_leaf_indices_, axis=0)
            treeWeights = (sample_leaf_indices == self.train_leaf_indices_) / n
            weights = np.sum(treeWeights, axis=1) / self.n_estimators
        else:
            n = np.sum(sample_leaf_indices == self.train_leaf_indices_)
            treeWeights = (sample_leaf_indices == self.train_leaf_indices_) / n
            weights = np.sum(treeWeights, axis=1)
        
        weightPosIndex = np.where(weights > 0)[0]
        weightsPos = weights[weightPosIndex]

        return (weightsPos, weightPosIndex)
