"""
Regression test suite for AUX Protocol.

This module contains tests that ensure backward compatibility and prevent
regressions when making changes to the AUX Protocol implementation.
"""

# Test categories
BACKWARD_COMPATIBILITY = "backward_compatibility"
PERFORMANCE_REGRESSION = "performance_regression"
API_STABILITY = "api_stability"
DATA_FORMAT_COMPATIBILITY = "data_format_compatibility"

# Version markers
CURRENT_VERSION = "2.0.0"
LEGACY_VERSIONS = ["1.0.0", "1.1.0", "1.2.0"]
SUPPORTED_VERSIONS = LEGACY_VERSIONS + [CURRENT_VERSION]

# Compatibility test configurations
COMPATIBILITY_TEST_CONFIG = {
    "enable_legacy_support": True,
    "strict_validation": False,
    "deprecated_warnings": True,
    "migration_guidance": True
}
