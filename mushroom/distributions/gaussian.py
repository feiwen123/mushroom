import numpy as np
from .distribution import Distribution
from scipy.stats import multivariate_normal


class GaussianDistribution(Distribution):
    """
    Gaussian distribution with fixed covariance matrix. The parameters
    vector represents only the mean.
    """
    def __init__(self, mu, sigma):
        self._mu = mu
        self._sigma = sigma
        self.inv_sigma = np.linalg.inv(sigma)

    def sample(self):
        return np.random.multivariate_normal(self._mu, self._sigma)

    def log_pdf(self, theta):
        return multivariate_normal.logpdf(theta, self._mu, self._sigma)

    def __call__(self, theta):
        return multivariate_normal.pdf(theta, self._mu, self._sigma)

    def mle(self, theta, weights=None):
        if weights is None:
            self._mu = np.mean(theta, axis=0)
        else:
            self._mu = weights.dot(theta) / np.sum(weights)

    def diff_log(self, theta):
        delta = theta - self._mu
        g = self.inv_sigma.dot(delta)

        return g

    def get_parameters(self):
        return self._mu

    def set_parameters(self, rho):
        self._mu = rho

    @property
    def parameters_size(self):
        return len(self._mu)


class GaussianDiagonalDistribution(Distribution):
    """
    Gaussian distribution with diagonal covariance matrix. The parameters
    vector represents the mean and the standard deviation for each dimension.
    """
    def __init__(self, mu, std):
        assert(len(std.shape) == 1)
        self._mu = mu
        self._std = std

    def sample(self):
        sigma = np.diag(self._std**2)
        return np.random.multivariate_normal(self._mu, sigma)

    def log_pdf(self, theta):
        sigma = np.diag(self._std ** 2)
        return multivariate_normal.logpdf(theta, self._mu, sigma)

    def __call__(self, theta):
        sigma = np.diag(self._std ** 2)
        return multivariate_normal.pdf(theta, self._mu, sigma)

    def mle(self, theta, weights=None):
        if weights is None:
            self._mu = np.mean(theta, axis=0)
            self._std = np.std(theta, axis=0)
        else:
            sumD = np.sum(weights)
            sumD2 = np.sum(weights**2)
            Z = sumD - sumD2 / sumD

            self._mu = weights.dot(theta) / sumD

            delta2 = (theta - self._mu)**2
            self._std = np.sqrt(weights.dot(delta2) / Z)

    def diff_log(self, theta):
        n_dims = len(self._mu)

        sigma = self._std**2

        g = np.empty(self.parameters_size)

        delta = theta - self._mu

        g_mean = delta / sigma
        g_cov = delta**2 / (self._std**3) - 1 / self._std

        g[:n_dims] = g_mean
        g[n_dims:] = g_cov
        return g

    def get_parameters(self):
        rho = np.empty(self.parameters_size)
        n_dims = len(self._mu)

        rho[:n_dims] = self._mu
        rho[n_dims:] = self._std

        return rho

    def set_parameters(self, rho):
        n_dims = len(self._mu)
        self._mu = rho[:n_dims]
        self._std = rho[n_dims:]

    @property
    def parameters_size(self):
        return 2 * len(self._mu)


class GaussianCholeskyDistribution(Distribution):
    """
    Gaussian distribution with full covariance matrix. The parameters
    vector represents the mean and the Cholesky decomposition of the
    covariance matrix. This parametrization enforce the covariance matrix to be
    positive definite.
    """
    def __init__(self, mu, sigma):
        self._mu = mu
        self._chol_sigma = np.linalg.cholesky(sigma)

    def sample(self):
        sigma = self._chol_sigma.dot(self._chol_sigma.T)
        return np.random.multivariate_normal(self._mu, sigma)

    def log_pdf(self, theta):
        sigma = self._chol_sigma.dot(self._chol_sigma.T)
        return multivariate_normal.logpdf(theta, self._mu, sigma)

    def __call__(self, theta):
        sigma = self._chol_sigma.dot(self._chol_sigma.T)
        return multivariate_normal.pdf(theta, self._mu, sigma)

    def mle(self, theta, weights=None):
        if weights is None:
            self._mu = np.mean(theta, axis=0)
            sigma = np.cov(theta)
        else:
            sumD = np.sum(weights)
            sumD2 = np.sum(weights**2)
            Z = sumD - sumD2 / sumD

            self._mu = weights.dot(theta) / sumD

            delta = theta - self._mu

            sigma = delta.T.dot(np.diag(weights)).dot(delta) / Z

        self._chol_sigma = np.linalg.cholesky(sigma)

    def diff_log(self, theta):
        n_dims = len(self._mu)
        inv_chol = np.linalg.inv(self._chol_sigma)
        inv_sigma = inv_chol.T.dot(inv_chol)

        g = np.empty(self.parameters_size)

        delta = theta - self._mu
        g_mean = inv_sigma.dot(delta)

        delta_a = np.reshape(delta, (-1, 1))
        delta_b = np.reshape(delta, (1, -1))

        S = inv_chol.dot(delta_a).dot(delta_b).dot(inv_sigma)

        g_cov = S - np.diag(np.diag(inv_chol))

        g[:n_dims] = g_mean
        g[n_dims:] = g_cov.T[np.tril_indices(n_dims)]

        return g

    def get_parameters(self):
        rho = np.empty(self.parameters_size)
        n_dims = len(self._mu)

        rho[:n_dims] = self._mu
        rho[n_dims:] = self._chol_sigma[np.tril_indices(n_dims)]

        return rho

    def set_parameters(self, rho):
        n_dims = len(self._mu)
        self._mu = rho[:n_dims]
        self._chol_sigma[np.tril_indices(n_dims)] = rho[n_dims:]

    @property
    def parameters_size(self):
        n_dims = len(self._mu)

        return 2 * n_dims + (n_dims * n_dims - n_dims) // 2
