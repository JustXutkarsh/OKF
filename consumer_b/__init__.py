"""Consumer B: read-only critical analysis agent over the OKF bundle.

Independent component: shares nothing with the producer, validator, or
Consumer A except the okf/ directory on disk. Own copy of every module.
"""

__all__ = ["__version__", "NOT_COVERED_SENTENCE"]

__version__ = "0.1.0"

# The exact sentence returned whenever the bundle cannot answer a question.
NOT_COVERED_SENTENCE = "This topic is not covered by the current knowledge bundle."
