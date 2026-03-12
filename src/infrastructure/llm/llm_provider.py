"""
Embedding model provider.

"""

import sys
import os

# Add the parent directory to sys.path to allow importing from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from typing import Any, Dict, Optional
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from agents.prompts.agent_prompts import prompt
from config import (
    models,
    OPENAI_API_KEY
)
from logger import setup_logger

logger = setup_logger(__name__)

class generate:
    def __init__(self, model_name: str = models["openai"]["chat"]["general"]):
        self.model_name = model_name
        self.llm = ChatOpenAI(model=model_name, api_key=OPENAI_API_KEY)

    def invoke(self, query: str, answer: str) -> Dict[str, Any]:
        try:
            chain = prompt | self.llm | JsonOutputParser()

            logger.info("Generated answer for query: %s", query)

            return chain.invoke({
                "query": query,
                "answer": answer
            })

        except Exception as e:
            logger.error("Failed to generate answer: %s", e)
            return None

generator = generate()
        
        
