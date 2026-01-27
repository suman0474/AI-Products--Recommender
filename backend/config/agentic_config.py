"""
Agentic Configuration
"""
import os
import logging

logger = logging.getLogger(__name__)

class AgenticConfig:
    """Centralized configuration for agentic workflows and LLM operations"""

    # LLM Model Configuration (Multi-tier approach)
    DEFAULT_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gemini-2.5-flash")
    PRO_MODEL = os.getenv("PRO_LLM_MODEL", "gemini-2.5-flash")
    LITE_MODEL = os.getenv("LITE_LLM_MODEL", "gemini-2.5-flash")
    FALLBACK_MODEL = os.getenv("FALLBACK_LLM_MODEL", "gemini-2.5-flash")

    # Google API Configuration
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # Model Temperature Settings
    DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.1"))
    CREATIVE_TEMPERATURE = float(os.getenv("CREATIVE_TEMPERATURE", "0.7"))

    # Timeout Configuration (in seconds)
    DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "30"))
    LONG_TIMEOUT = int(os.getenv("LONG_TIMEOUT", "120"))
    PARALLEL_ANALYSIS_TIMEOUT = int(os.getenv("PARALLEL_ANALYSIS_TIMEOUT", "300"))

    # Parallel Processing Configuration
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "5"))
    MAX_VENDORS_TO_ANALYZE = int(os.getenv("MAX_VENDORS_TO_ANALYZE", "5"))

    # ChromaDB Configuration
    CHROMADB_HOST = os.getenv("CHROMADB_HOST", "localhost")
    CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))
    CHROMADB_TIMEOUT = int(os.getenv("CHROMADB_TIMEOUT", "30"))

    # Retry Configuration
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.0"))

    # Workflow Configuration
    MAX_WORKFLOW_RETRIES = int(os.getenv("MAX_WORKFLOW_RETRIES", "2"))
    WORKFLOW_TIMEOUT = int(os.getenv("WORKFLOW_TIMEOUT", "300"))

    # RAG Configuration
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
    RAG_SCORE_THRESHOLD = float(os.getenv("RAG_SCORE_THRESHOLD", "0.7"))

    @classmethod
    def validate(cls):
        """
        Validate required configuration settings.

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        if not cls.GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY is required. "
                "Please set it in your .env file or environment variables."
            )

        # Validate temperature ranges
        if not (0.0 <= cls.DEFAULT_TEMPERATURE <= 2.0):
            raise ValueError(
                f"DEFAULT_TEMPERATURE must be between 0.0 and 2.0 (got {cls.DEFAULT_TEMPERATURE})"
            )

        if not (0.0 <= cls.CREATIVE_TEMPERATURE <= 2.0):
            raise ValueError(
                f"CREATIVE_TEMPERATURE must be between 0.0 and 2.0 (got {cls.CREATIVE_TEMPERATURE})"
            )

        # Validate positive integers
        if cls.MAX_WORKERS < 1:
            raise ValueError(f"MAX_WORKERS must be at least 1 (got {cls.MAX_WORKERS})")

        if cls.DEFAULT_TIMEOUT < 1:
            raise ValueError(f"DEFAULT_TIMEOUT must be at least 1 (got {cls.DEFAULT_TIMEOUT})")

        if cls.RAG_TOP_K < 1:
            raise ValueError(f"RAG_TOP_K must be at least 1 (got {cls.RAG_TOP_K})")

    @classmethod
    def print_config(cls):
        """Print current configuration (safe - hides API key)"""
        logger.info("=" * 60)
        logger.info("AGENTIC CONFIGURATION")
        logger.info("=" * 60)
        logger.info(f"Google API Key: {'*' * 20}{cls.GOOGLE_API_KEY[-4:] if cls.GOOGLE_API_KEY else 'NOT SET'}")
        logger.info(f"Default Model: {cls.DEFAULT_MODEL}")
        logger.info(f"Pro Model: {cls.PRO_MODEL}")
        logger.info(f"Lite Model: {cls.LITE_MODEL}")
        logger.info(f"Fallback Model: {cls.FALLBACK_MODEL}")
        logger.info(f"Default Temperature: {cls.DEFAULT_TEMPERATURE}")
        logger.info(f"Creative Temperature: {cls.CREATIVE_TEMPERATURE}")
        logger.info(f"Default Timeout: {cls.DEFAULT_TIMEOUT}s")
        logger.info(f"Long Timeout: {cls.LONG_TIMEOUT}s")
        logger.info(f"Parallel Analysis Timeout: {cls.PARALLEL_ANALYSIS_TIMEOUT}s")
        logger.info(f"Max Workers: {cls.MAX_WORKERS}")
        logger.info(f"Max Vendors to Analyze: {cls.MAX_VENDORS_TO_ANALYZE}")
        logger.info(f"ChromaDB Host: {cls.CHROMADB_HOST}")
        logger.info(f"ChromaDB Port: {cls.CHROMADB_PORT}")
        logger.info(f"ChromaDB Timeout: {cls.CHROMADB_TIMEOUT}s")
        logger.info(f"RAG Top K: {cls.RAG_TOP_K}")
        logger.info(f"RAG Score Threshold: {cls.RAG_SCORE_THRESHOLD}")
        logger.info("=" * 60)
