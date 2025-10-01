"""Custom exceptions for the Budget Agent application.

This module centralizes all domain-specific exceptions to promote
reuse, clarity, and consistent error handling across the application.
"""


class BudgetAgentException(Exception):
    """Base exception for all Budget Agent errors."""

    pass


# External Service Errors


class ExternalServiceError(BudgetAgentException):
    """Base exception for external service failures."""

    pass


class MonarchMoneyError(ExternalServiceError):
    """Exception for Monarch Money API failures."""

    pass


class MonarchMoneyLoginError(MonarchMoneyError):
    """Exception for Monarch Money login failures."""

    pass


class MonarchMoneyDataError(MonarchMoneyError):
    """Exception for Monarch Money data retrieval failures."""

    pass


class DatabaseError(ExternalServiceError):
    """Exception for database operation failures."""

    pass


class DatabaseConnectionError(DatabaseError):
    """Exception for database connection failures."""

    pass


class DatabaseQueryError(DatabaseError):
    """Exception for database query failures."""

    pass


class LLMError(ExternalServiceError):
    """Exception for LLM API failures."""

    pass


class LLMTimeoutError(LLMError):
    """Exception for LLM API timeout."""

    pass


class LLMRateLimitError(LLMError):
    """Exception for LLM API rate limit exceeded."""

    pass


class LLMResponseError(LLMError):
    """Exception for invalid LLM response format."""

    pass


class EmailError(ExternalServiceError):
    """Exception for email sending failures."""

    pass


# Data Processing Errors


class DataProcessingError(BudgetAgentException):
    """Base exception for data processing failures."""

    pass


class DataValidationError(DataProcessingError):
    """Exception for data validation failures."""

    pass


class DataParsingError(DataProcessingError):
    """Exception for data parsing failures."""

    pass


class TransactionDataMissingError(DataProcessingError):
    """Exception for missing transaction data."""

    pass


class BudgetDataMissingError(DataProcessingError):
    """Exception for missing budget data."""

    pass


# Configuration Errors


class ConfigurationError(BudgetAgentException):
    """Exception for configuration-related failures."""

    pass
