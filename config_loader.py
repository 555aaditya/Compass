import yaml
import json
import os
from dotenv import load_dotenv

load_dotenv()

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def load_companies():
    with open("companies.json", "r") as f:
        return json.load(f)

CONFIG = load_config()
COMPANIES = load_companies()
