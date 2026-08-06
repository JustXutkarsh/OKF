"""Production backend API for the OKF geopolitics system.

Fourth component: composes the public interfaces of producer and the
consumers; owns transport concerns only (routing, auth, limits, logging,
metrics, jobs). Never duplicates consumer logic.
"""

__all__ = ["__version__"]

__version__ = "1.0.0"
