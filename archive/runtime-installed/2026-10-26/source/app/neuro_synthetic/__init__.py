"""Contracts, neural core, and durable records for the Flynn architecture."""

from .aggregator import NeuralActivityAggregator
from .lif_engine import LIFEngine, LIFParameters
from .neural_core import NeuralCore
from .pipeline import NeuralActivityPipeline
from .proprioceptive_transducer import SyntheticProprioceptiveTransducer
from .signed_connectome import SignedConnectome, build_signed_csr
from .sqlite_store import FlynnStore
from .world_runtime import FlynnWorldRuntime

__all__ = [
    "FlynnStore",
    "LIFEngine",
    "LIFParameters",
    "NeuralActivityAggregator",
    "NeuralActivityPipeline",
    "SyntheticProprioceptiveTransducer",
    "NeuralCore",
    "SignedConnectome",
    "FlynnWorldRuntime",
    "build_signed_csr",
]
