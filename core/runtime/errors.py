class ProviderError(RuntimeError):
    """Raised when a text generation provider fails."""


class ProviderConfigurationError(ProviderError):
    """Raised when the provider environment is incomplete."""
