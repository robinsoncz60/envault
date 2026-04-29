"""Shared base exception for all envault errors.

Each sub-module defines its own error class that inherits from EnvaultError,
making it easy to catch all envault-related errors in one place (e.g., in the
CLI layer) while still allowing fine-grained handling per module.
"""


class EnvaultError(Exception):
    """Base class for all envault exceptions."""


# Re-export sub-module errors here as a convenience so callers can do:
#   from envault.exceptions import CryptoError, PushError, ...
try:
    from envault.crypto import CryptoError  # noqa: F401
except ImportError:  # pragma: no cover
    pass

try:
    from envault.keystore import KeystoreError  # noqa: F401
except ImportError:  # pragma: no cover
    pass

try:
    from envault.storage import StorageError  # noqa: F401
except ImportError:  # pragma: no cover
    pass

try:
    from envault.config import ConfigError  # noqa: F401
except ImportError:  # pragma: no cover
    pass

try:
    from envault.versioning import VersioningError  # noqa: F401
except ImportError:  # pragma: no cover
    pass

try:
    from envault.bundle import BundleError  # noqa: F401
except ImportError:  # pragma: no cover
    pass

try:
    from envault.push import PushError  # noqa: F401
except ImportError:  # pragma: no cover
    pass

try:
    from envault.pull import PullError  # noqa: F401
except ImportError:  # pragma: no cover
    pass
