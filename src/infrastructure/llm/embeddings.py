"""
Embedding model provider.

"""

import sys
import os

# Add the parent directory to sys.path to allow importing from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from typing import Any
from langchain_openai import OpenAIEmbeddings
from config import (
    models,
    OPENAI_API_KEY
)
from logger import setup_logger

logger = setup_logger(__name__)

class Embeddings:
    """
    Embedding model provider.
    """

    def __init__(self, model_name: str = models["openai"]["embedding"]["default"]):
        self.model_name = model_name
        self.embeddings = OpenAIEmbeddings(model=model_name, api_key=OPENAI_API_KEY)

    def embed_query(self, text: str) -> list[float]:
        """
        Get embeddings for a given text.
        """
        try:
            return self.embeddings.embed_query(text)
        except Exception as e:
            logger.error("Failed to get embeddings: %s", e)
            return None