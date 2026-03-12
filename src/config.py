import yaml
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def load_yaml(file_path: Path) -> dict:
    """Reads a YAML file and returns it as a dictionary."""
    if not file_path.exists():
        print(f"Warning: Configuration file not found at {file_path}")
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file {file_path}: {e}")
            return {}

def get_config():
    """Loads all configuration files and returns a unified dictionary."""
    project_root = Path(__file__).parent.parent
    config_dir = project_root / "config"
    
    params = load_yaml(config_dir / "param.yaml")
    models = load_yaml(config_dir / "models.yaml")
    
    return {
        "params": params,
        "models": models,
        "env": dict(os.environ)
    }

# Global config instance for easy access
config = get_config()
params = config["params"]
models = config["models"]

# Qdrant 
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")

# Tavily
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Open AI API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# Timezone (used by web_search_tool for timestamp display)
TIMEZONE = "Asia/Colombo"