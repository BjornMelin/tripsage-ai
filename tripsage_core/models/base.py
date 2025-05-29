"""
Base model classes for TripSage (DEPRECATED).

This module is deprecated. Please use tripsage_core.models.base_core_model instead.
The models here are kept for backwards compatibility but will be removed in a
future version.
"""

import warnings

from tripsage_core.models.base_core_model import (
    TripSageBaseResponse as _TripSageBaseResponse,
)
from tripsage_core.models.base_core_model import (
    TripSageModel as _TripSageModel,
)

# Backwards compatibility - issue deprecation warnings
warnings.warn(
    "tripsage_core.models.base is deprecated. "
    "Use tripsage_core.models.base_core_model instead.",
    DeprecationWarning,
    stacklevel=2,
)


class TripSageModel(_TripSageModel):
    """Base model for all TripSage models (DEPRECATED)."""

    pass


class TripSageBaseResponse(_TripSageBaseResponse):
    """Base model for all TripSage API responses (DEPRECATED)."""

    pass
