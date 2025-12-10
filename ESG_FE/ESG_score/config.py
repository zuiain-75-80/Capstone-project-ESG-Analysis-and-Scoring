import os
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class ModelConfig:
    model_name: str = "vinai/phobert-base"

class ESGConfig:
    def __init__(self):
        self.category_labels = {
            'environment': ['Environmental Negative', 'Environmental Neutral', 'Environmental Positive'],
            'governance': ['Governance Negative', 'Governance Neutral', 'Governance Positive'],
            'social': ['Social Negative', 'Social Neutral', 'Social Positive']
        }