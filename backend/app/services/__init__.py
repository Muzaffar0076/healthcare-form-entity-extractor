"""
Backend services package.
"""

from .predictor import NERPredictor, predictor_instance

__all__ = ["NERPredictor", "predictor_instance"]
