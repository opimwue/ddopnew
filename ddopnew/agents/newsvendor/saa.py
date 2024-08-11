# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../nbs/41_NV_agents/10_NV_saa_agents.ipynb.

# %% auto 0
__all__ = ['BaseSAAagent', 'NewsvendorSAAagent', 'BasewSAAagent', 'NewsvendorRFwSAAagent']

# %% ../../../nbs/41_NV_agents/10_NV_saa_agents.ipynb 3
import logging

from abc import ABC, abstractmethod
from typing import Union, Optional, List
import numpy as np
import joblib
import os

from ...envs.base import BaseEnvironment
from ..base import BaseAgent
from ...utils import MDPInfo
from ...obsprocessors import FlattenTimeDimNumpy

from sklearn.ensemble import RandomForestRegressor
from sklearn.utils.validation import check_array


# %% ../../../nbs/41_NV_agents/10_NV_saa_agents.ipynb 4
class BaseSAAagent(BaseAgent):

    """
    Base class for Sample Average Approximation Agents, implementing the main method
    to find the quntile of some (weighted) empirical distribution.
    """

    def __init__(self,
                 environment_info: MDPInfo,
                 obsprocessors: Optional[List[object]] = None,
                 postprocessors: Optional[List[object]] = None,
                 agent_name: str | None = None,
                 ):

        super().__init__(environment_info, obsprocessors, postprocessors, agent_name)

        # check if FlattenTimeDimNumpy in obsprocessors
        if not any(isinstance(p, FlattenTimeDimNumpy) for p in self.obsprocessors):
            self.add_obsprocessor(FlattenTimeDimNumpy(allow_2d=True))

    def find_weighted_quantiles(self, weights, weightPosIndices, sl, y):
        
        """
        Find the weighted quantile of a range of data y. 
        It assumes that all arrays are of shape (n_samples, n_outputs). Note that it
        has not been tested for n_outputs > 1.
        """

        # test shapes have lenght 2 with error
        assert len(y.shape) == 2, "y should be of shape (n_samples, n_outputs)"

        n_outputs = y.shape[1]

        yWeightPos = y[weightPosIndices]

        if self.print:
            print(yWeightPos)
        
        q = []

        if len(weights.shape) == 1:
            weights = weights.reshape(-1, 1)
        
        for i in range(n_outputs):
            
            indicesYSort = np.argsort(yWeightPos[:, i])
            
            ySorted = yWeightPos[indicesYSort, i]
            
            distributionFunction = np.cumsum(weights[indicesYSort, i])

            decisionIndex = np.where(distributionFunction >= sl)[0][0]
            
            q.append(ySorted[decisionIndex])

        q = np.array(q)
        
        return q
    
    def _validate_X_predict(self, X):
        
        """Validate X data before prediction"""

        X = check_array(X)

        n_features = X.shape[1]
        if self.n_features_ != n_features:
            raise ValueError("Number of features of the model must match the input. "
                             "Model n_features is %s and input n_features is %s "
                             % (self.n_features_, n_features))
        return X

# %% ../../../nbs/41_NV_agents/10_NV_saa_agents.ipynb 8
class NewsvendorSAAagent(BaseSAAagent):

    """
    Newsvendor agent that uses Sample Average Approximation to find the quantile of the empirical distribution

    """

    def __init__(self,
                environment_info: MDPInfo,
                cu: float | np.ndarray, # underage cost
                co: float | np.ndarray, # overage cost
                obsprocessors: list[object] | None = None,
                postprocessors: list[object] | None = None,
                agent_name: str = "SAA",
                ):

            # if float, convert to array
            cu = self.convert_to_numpy_array(cu)
            co = self.convert_to_numpy_array(co)

            self.sl = cu / (cu + co)
            self.fitted = False

            super().__init__(environment_info, obsprocessors, postprocessors, agent_name)

    def fit(self,
            X: np.ndarray, # features will be ignored
            Y: np.ndarray) -> None:

        """

        Fit the agent to the data. The agent will find the quantile of the empirical distribution of the data.

        """

        # # potential line:
        # X, y = self._validate_data(X, y, multi_output=True)

        weights = np.ones(Y.shape)/Y.shape[0]
        weightPosIndices = np.arange(Y.shape[0])
        
        self.quantiles = self.find_weighted_quantiles(weights, weightPosIndices, self.sl, Y)

        self.fitted = True

    def draw_action_(self, 
                    observation: np.ndarray) -> np.ndarray: #
        """

        Draw an action from the quantile of the empirical distribution.

        """


        if self.fitted == False:
            return np.array([0.0])

        return self.quantiles


    def save(self,
                path: str, # The directory where the file will be saved.
                overwrite: bool=True): # Allow overwriting; if False, a FileExistsError will be raised if the file exists.
        
        """
        Save the quantiles to a file in the specified directory.

        """

        if not self.fitted:
            raise ValueError("Agent has not been fitted yet")

        os.makedirs(path, exist_ok=True)
        
        full_path = os.path.join(path, "saa_quantiles.npy")
        
        if os.path.exists(full_path):
            if not overwrite:
                raise FileExistsError(f"The file {full_path} already exists and will not be overwritten.")
            else:
                logging.warning(f"Overwriting file {full_path}")
                
        np.save(full_path, self.quantiles)

    def load(self, path: str): # Only the path to the folder is needed, not the file itself

        """
        Load the quantiles from a file.
        

        """

        full_path = os.path.join(path, "saa_quantiles.npy")
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"The file {full_path} does not exist.")
        
        try:
            self.quantiles = np.load(full_path)
            self.fitted = True  # Assuming that loading the quantiles means the agent is now 'fitted'
            logging.info(f"Quantiles loaded successfully from {full_path}")
        except Exception as e:
            raise ValueError(f"An error occurred while loading the file: {e}")

# %% ../../../nbs/41_NV_agents/10_NV_saa_agents.ipynb 15
class BasewSAAagent(BaseSAAagent):


    """
    Base class for weighted Sample Average Approximation (wSAA) Agents

    """

    def __init__(self,
                environment_info: MDPInfo,
                cu: float | np.ndarray,
                co: float | np.ndarray,
                obsprocessors: list[object] | None = None,
                postprocessors: list[object] | None = None,
                agent_name: str = "wSAA",
                ):  #


        # if float, convert to array
        self.cu = np.array([cu]) if isinstance(cu, float) else cu
        self.co = np.array([co]) if isinstance(co, float) else co

        cu = self.convert_to_numpy_array(cu)
        co = self.convert_to_numpy_array(co)

        self.sl = cu / (cu + co)
        
        self.fitted = False

        super().__init__(environment_info, obsprocessors, postprocessors, agent_name)

    def fit(self,
            X: np.ndarray,
            Y: np.ndarray): #

        """

        Fit the agent to the data. The function will call _get_fitted_model which will
        train a machine learning model to determine the sample weightes (e.g., kNN, DT, RF).

        """
        
        # # potential line:
        # X, y = self._validate_data(X, y, multi_output=True)

        # get FlattenTimeDimNumpy obsprocessor
        flatten_obsprocessor = [p for p in self.obsprocessors if isinstance(p, FlattenTimeDimNumpy)][0]

        X = flatten_obsprocessor(X)

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

    def draw_action_(self, 
                    observation: np.ndarray) -> np.ndarray: # 

        """

        Draw an action based on the fitted model (see predict method)

        """

        if self.fitted == False:
            return np.array([0.0])
        
        return self.predict(observation)
    
    @abstractmethod
    def _get_fitted_model(self, X, y):
        """Initialise the underlying model - depending on the underlying machine learning model"""

    @abstractmethod
    def _calc_weights(self, sample):
        """Calculate the sample weights - depending on the underlying machine learning model"""

    def predict(self, 
                X: np.ndarray
    ) -> np.ndarray: #
        """Predict value for X by finding the quantiles of the empirical distribution based
        on the sample weights predicted by the underlying machine learning model.
        """

        X = self._validate_X_predict(X)  

        if self.print:
            print("X: ", X)

        weightsDataList = [self._calc_weights(row) for row in X]

        if self.print:
            print("weightsDataList: ", weightsDataList)

        pred = [self.find_weighted_quantiles(weights, weightPosIndices, self.sl, self.Y_) 
                for weights, weightPosIndices in weightsDataList]


        pred = np.array(pred)   

        if self.print:
            print("Predicted quantiles: ", pred)

        return pred

    def save(self,
                path: str, # The directory where the file will be saved.
                overwrite: bool=True): # Allow overwriting; if False, a FileExistsError will be raised if the file exists.
        """
        Save the scikit-learn model to a file in the specified directory.

        """

        if not self.fitted:
            raise ValueError("Agent has not been fitted yet")

        if not hasattr(self, 'model_') or self.model_ is None:
            raise ValueError("Agent has no model to save.")

        # Create directory if it does not exist
        os.makedirs(path, exist_ok=True)
        
        # Construct the file path using os.path.join for better cross-platform compatibility
        full_path = os.path.join(path, "model.joblib")
        
        if os.path.exists(full_path):
            if not overwrite:
                raise FileExistsError(f"The file {full_path} already exists and will not be overwritten.")
            else:
                logging.warning(f"Overwriting file {full_path}")
        
        # Save the model using joblib
        joblib.dump(self.model_, full_path)

    def load(self, path: str): # Only the path to the folder is needed, not the file itself
        """
        Load the scikit-learn model from a file.

        """
        
        # Construct the file path
        full_path = os.path.join(path, "model.joblib")
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"The file {full_path} does not exist.")
        
        try:
            # Load the model using joblib
            self.model_ = joblib.load(full_path)
            self.fitted = True  # Assuming that loading the model means the agent is now 'fitted'
            logging.info(f"Model loaded successfully from {full_path}")
        except Exception as e:
            raise ValueError(f"An error occurred while loading the model: {e}")

# %% ../../../nbs/41_NV_agents/10_NV_saa_agents.ipynb 24
class NewsvendorRFwSAAagent(BasewSAAagent):

    """

    Newsvendor agent that uses weighted Sample Average Approximation based on Random Forest

    """

    def __init__(self,
                environment_info: MDPInfo,
                cu: float | np.ndarray, # underage cost
                co: float | np.ndarray, # overage cost
                obsprocessors: list[object] | None = None, # List of obsprocessors to apply to the observation
                postprocessors: list[object] | None = None, # List of postprocessors to apply to the action
                n_estimators: int = 100,# The number of trees in the forest.
                criterion: str = "squared_error", # Function to measure the quality of a split.
                max_depth: int | None = None, # Maximum depth of the tree; None means unlimited.
                min_samples_split: int = 2, # Minimum samples required to split a node.
                min_samples_leaf: int = 1, # Minimum samples required to be at a leaf node.
                min_weight_fraction_leaf: float = 0.0, # Minimum weighted fraction of the total weights at a leaf node.
                max_features: int | float | str | None = 1.0, # Number of features to consider when looking for the best split.
                max_leaf_nodes: int | None = None, # Maximum number of leaf nodes; None means unlimited.
                min_impurity_decrease: float = 0.0, # Minimum impurity decrease required to split a node.
                bootstrap: bool = True, # Whether to use bootstrap samples when building trees.
                oob_score: bool = False, # Whether to use out-of-bag samples to estimate R^2 on unseen data.
                n_jobs: int | None = None, # Number of jobs to run in parallel; None means 1.
                random_state: int | np.random.RandomState | None = None, # Controls randomness for bootstrapping and feature sampling.
                verbose: int = 0, # Controls the verbosity when fitting and predicting.
                warm_start: bool = False, # If True, reuse solution from previous fit and add more estimators.
                ccp_alpha: float = 0.0, # Complexity parameter for Minimal Cost-Complexity Pruning.
                max_samples: int | float | None = None, # Number of samples to draw when bootstrap is True.
                monotonic_cst: np.ndarray | None = None, # Monotonic constraints for features.
                agent_name: str = "wSAA", # Default wSAA, change if it is needed to differentiate among different ML models
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

        super().__init__(environment_info, cu, co, obsprocessors, postprocessors, agent_name)

    def _get_fitted_model(self,
                            X: np.ndarray,
                            Y: np.ndarray): #

        """

        Fit the underlying machine learning model using all X and Y data in the train set.

        """

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

        self.model_ = model.fit(X, Y)
        self.train_leaf_indices_ = model.apply(X)

    def _calc_weights(self, sample: np.ndarray) -> tuple[np.ndarray, np.ndarray]: #

        """
        Calculate the sample weights based on the Random Forest model.

        """

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
