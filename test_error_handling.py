"""Tests for error handling and retry logic.

This module tests the new error handling capabilities added in Step 4.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from services.api.app.exceptions import (
    DatabaseConnectionError,
    DatabaseQueryError,
    EmailError,
    LLMError,
    LLMResponseError,
    LLMTimeoutError,
    MonarchMoneyDataError,
    MonarchMoneyLoginError,
)


class TestCustomExceptions:
    """Test custom exception hierarchy."""

    def test_llm_error_inheritance(self):
        """Test that LLM errors inherit from base exception."""
        error = LLMError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_database_error_inheritance(self):
        """Test that database errors inherit from base exception."""
        error = DatabaseConnectionError("Connection failed")
        assert isinstance(error, Exception)
        assert str(error) == "Connection failed"

    def test_monarch_money_error_inheritance(self):
        """Test that MonarchMoney errors inherit from base exception."""
        error = MonarchMoneyLoginError("Login failed")
        assert isinstance(error, Exception)
        assert str(error) == "Login failed"


class TestLLMRetryLogic:
    """Test LLM API retry logic and timeout handling."""

    @pytest.mark.asyncio
    async def test_call_llm_timeout_handling(self):
        """Test that call_llm handles timeouts correctly."""
        from services.api.app.agent.agent_utilities import call_llm
        from services.api.app.domain.prompts import SYSTEM_PROMPT

        # Create a mock prompt object
        mock_prompt = Mock()
        mock_prompt.prompt = "Test prompt: {test_var}"

        # Mock the AsyncGroq client to raise TimeoutError
        with patch(
            "services.api.app.agent.agent_utilities.AsyncGroq"
        ) as mock_groq_class:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.side_effect = TimeoutError(
                "Request timed out"
            )
            mock_groq_class.return_value = mock_client

            # Should raise LLMTimeoutError after retries
            with pytest.raises(LLMTimeoutError) as exc_info:
                await call_llm(
                    prompt_obj=mock_prompt,
                    test_var="test",
                    timeout=1,  # Short timeout
                )

            assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_call_llm_empty_response(self):
        """Test that call_llm handles empty responses."""
        from services.api.app.agent.agent_utilities import call_llm

        mock_prompt = Mock()
        mock_prompt.prompt = "Test prompt: {test_var}"

        # Mock the AsyncGroq client to return empty response
        with patch(
            "services.api.app.agent.agent_utilities.AsyncGroq"
        ) as mock_groq_class:
            mock_client = AsyncMock()
            mock_completion = Mock()
            mock_completion.choices = []  # Empty choices
            mock_client.chat.completions.create.return_value = mock_completion
            mock_groq_class.return_value = mock_client

            # Should raise LLMResponseError after retries
            with pytest.raises(LLMResponseError) as exc_info:
                await call_llm(prompt_obj=mock_prompt, test_var="test")

            assert "empty response" in str(exc_info.value).lower()


class TestDatabaseErrorHandling:
    """Test database connection and query error handling."""

    def test_mongo_client_connection_failure(self):
        """Test that MongoDBClient handles connection failures."""
        from pymongo.errors import ServerSelectionTimeoutError
        from services.api.pipelines.mongo_client import MongoDBClient

        # Mock MongoClient to raise connection error
        with patch(
            "services.api.pipelines.mongo_client.MongoClient"
        ) as mock_mongo_class:
            mock_client = Mock()
            mock_client.server_info.side_effect = ServerSelectionTimeoutError(
                "Connection timeout"
            )
            mock_mongo_class.return_value = mock_client

            # Should raise DatabaseConnectionError
            with pytest.raises(DatabaseConnectionError) as exc_info:
                MongoDBClient()

            assert "failed to connect" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_async_mongo_client_query_failure(self):
        """Test that AsyncMongoDBClient handles query failures."""
        from pymongo.errors import OperationFailure
        from services.api.pipelines.mongo_client import AsyncMongoDBClient

        # Mock AsyncIOMotorClient
        with patch(
            "services.api.pipelines.mongo_client.AsyncIOMotorClient"
        ) as mock_motor_class:
            mock_client = Mock()
            mock_db = Mock()
            mock_collection = Mock()

            # Mock the cursor to raise OperationFailure
            mock_cursor = Mock()
            mock_cursor.to_list = AsyncMock(
                side_effect=OperationFailure("Query failed")
            )
            mock_collection.find.return_value = mock_cursor

            mock_db.__getitem__ = Mock(return_value=mock_collection)
            mock_client.__getitem__ = Mock(return_value=mock_db)
            mock_motor_class.return_value = mock_client

            # Create client and test import_budget_data
            client = AsyncMongoDBClient()

            # Should raise DatabaseQueryError after retries
            with pytest.raises(DatabaseQueryError) as exc_info:
                await client.import_budget_data()

            assert "failed to import budget data" in str(exc_info.value).lower()


class TestEmailRetryLogic:
    """Test email sending retry logic."""

    @pytest.mark.asyncio
    async def test_send_email_smtp_failure(self):
        """Test that send_email_async handles SMTP failures."""
        import smtplib
        from services.api.app.agent.agent_utilities import SendEmail

        # Create a mock EmailInfo
        mock_email_info = Mock()
        mock_email_info.from_ = "test@example.com"
        mock_email_info.to = "recipient@example.com"
        mock_email_info.subject = "Test Subject"
        mock_email_info.body = "Test body"

        # Mock SMTP to raise SMTPException
        with patch("smtplib.SMTP") as mock_smtp_class:
            mock_smtp = Mock()
            mock_smtp.__enter__ = Mock(return_value=mock_smtp)
            mock_smtp.__exit__ = Mock(return_value=False)
            mock_smtp.send_message.side_effect = smtplib.SMTPException(
                "SMTP error occurred"
            )
            mock_smtp_class.return_value = mock_smtp

            email_sender = SendEmail(mock_email_info)

            # Should raise EmailError after retries
            with pytest.raises(EmailError) as exc_info:
                await email_sender.send_email_async()

            assert "smtp error" in str(exc_info.value).lower()


class TestMonarchMoneyErrorHandling:
    """Test MonarchMoney API error handling."""

    @pytest.mark.asyncio
    async def test_monarch_login_retry_logic(self):
        """Test that monarch_login retries on failures."""
        from services.api.pipelines.import_functions import MonarkImport

        monark = MonarkImport()

        # Mock the monarch.login to raise exception
        with patch.object(
            monark.monarch, "login", side_effect=Exception("Network error")
        ):
            # Should raise MonarchMoneyLoginError after retries
            with pytest.raises(MonarchMoneyLoginError) as exc_info:
                await monark.monarch_login(pw="test", user="test@example.com")

            assert "failed to login" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_txn_data_error(self):
        """Test that get_txn handles data retrieval errors."""
        from services.api.pipelines.import_functions import MonarkImport

        monark = MonarkImport()
        monark._logged_in = True

        # Mock get_transactions to raise exception
        with patch.object(
            monark.monarch,
            "get_transactions",
            side_effect=Exception("API rate limit"),
        ):
            # Should raise MonarchMoneyDataError after retries
            with pytest.raises(MonarchMoneyDataError) as exc_info:
                await monark.get_txn()

            assert "failed to retrieve transactions" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
