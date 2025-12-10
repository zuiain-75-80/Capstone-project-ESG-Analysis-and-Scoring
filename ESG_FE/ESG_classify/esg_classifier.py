"""
ESG Text Classification Module
Handles text classification for Environmental, Social, and Governance categories
"""
import os
import re
import pandas as pd
import numpy as np
import json
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification, 
    BertTokenizer, BertForSequenceClassification,
    DistilBertTokenizer, DistilBertForSequenceClassification,
    RobertaForSequenceClassification,
    XLMRobertaTokenizer, XLMRobertaForSequenceClassification,
    ElectraTokenizer, ElectraForSequenceClassification,
    DebertaV2ForSequenceClassification
)
import torch
import torch.nn.functional as F

from gensim.utils import simple_preprocess
from pyvi import ViTokenizer
from typing import Dict, List

import warnings
warnings.filterwarnings("ignore")

MODEL_MAP = {
    # DistilBERT
    "distilbert": (DistilBertForSequenceClassification, DistilBertTokenizer),
    
    # RoBERTa & PhoBERT
    "roberta": (RobertaForSequenceClassification, AutoTokenizer),
    "phobert": (RobertaForSequenceClassification, AutoTokenizer),
    
    # XLM-R
    "xlm-roberta": (XLMRobertaForSequenceClassification, XLMRobertaTokenizer),
    "visobert": (XLMRobertaForSequenceClassification, XLMRobertaTokenizer),
    
    # Electra
    "electra": (ElectraForSequenceClassification, ElectraTokenizer),
    
    # DeBERTa
    "deberta": (DebertaV2ForSequenceClassification, AutoTokenizer),

    # BERT
    "bert": (BertForSequenceClassification, BertTokenizer),
    
    
    # Fallback (default Auto)
    "auto": (AutoModelForSequenceClassification, AutoTokenizer)
}

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


def detect_model_type(model_name: str) -> str:
    name = model_name.lower()
    for key in MODEL_MAP.keys():
        if key in name:
            return key
    return "auto"  # fallback

class ESGClassifier:
    """ESG Text Classifier using rule-based approach"""
    
    def __init__(self, model_path):
        self.model = None
        self.tokenizer = None
        self.classifier = None
        self.vi_tokenizer = ViTokenizer
        self.load_model(model_path)
    
    def load_model(self, model_path: str):
        """Load tokenizer and create classifier"""
        try:
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model path không tồn tại: {model_path}")
            print(f"Loading model from: {model_path}")

            model_type = detect_model_type(model_path)
            ModelClass, TokenizerClass = MODEL_MAP[model_type]
            self.model = ModelClass.from_pretrained(model_path,
                            num_labels=4, device_map="cuda"
                        )
            self.tokenizer = TokenizerClass.from_pretrained(model_path)
            metadata_path = os.path.join(model_path, 'model_metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    self.label_names = metadata.get('label_names', [])

        except Exception as e:
            print(f"Error loading model: {e}")
            self.tokenizer = None
            self.classifier = None
        
    def preproces_text(self,text) -> str:
        """preprocess Vietnamese text"""
        if pd.isna(text):
            return ""
    
        tokens = simple_preprocess(text)
        text = ' '.join(tokens)
        text = self.vi_tokenizer.tokenize(text)
        
        return text
    
    def preprocess_dataframe(self, df: pd.DataFrame, text_column: str) -> pd.DataFrame:
        """Preprocess toàn bộ dataframe"""
        df = df.copy()
        df[text_column] = df[text_column].apply(self.preproces_text)
        return df

    def classify_text(self, unlabeled_texts: List[str]) -> pd.DataFrame:
        try:
            LABEL_MAP = {0: "Irrelevant", 1: "Environment", 2: "Social", 3: "Governance"}            
            processed_texts = [self.preproces_text(text) for text in unlabeled_texts]
            results = self.batch_predict(processed_texts)
            df = pd.DataFrame(results)
            df["label_name"] = df["class_id"].map(LABEL_MAP)
            counts = df["label_name"].value_counts().reindex(
                ["Environment", "Social", "Governance", "Irrelevant"], fill_value=0
            ).to_dict()
            data = pd.DataFrame(columns=["text","label"])
            data["text"] = unlabeled_texts
            data["label"] = df["label_name"]
            return counts, data

        except Exception as e:
            print(f"Classification error: {e}")
            return self._get_default_count(), None
    
    
    def _get_default_count(self):
        """Get default Number of sentences for invalid input"""
        return {
            "Environmental": 0,
            "Social": 0, 
            "Governance": 0,
            "Irrelevant": 100
        }
    
    def predict(self, text: str) -> Dict[str, float]:
        """Dự đoán cho một text"""
        if self.model is None or self.tokenizer is None:
            raise ValueError("Model chưa được khởi tạo hoặc load.")
        
        inputs = self.tokenizer(
            text, 
            return_tensors='pt', 
            truncation=True, 
            padding=True,
            max_length=256
        ).to("cuda")
        
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=-1)[0]
            predicted_class_idx = torch.argmax(probabilities).item()

        results = {
                "class": self.label_names[predicted_class_idx],
                "confidence": probabilities[predicted_class_idx].item(),
                "class_id": predicted_class_idx
            }
        
        return results
    

    def batch_predict(self, texts: List[str], batch_size: int = 32) -> List[Dict[str, float]]:
        if self.model is None or self.tokenizer is None:
            raise ValueError("Model chưa được khởi tạo hoặc load.")
        
        self.model.eval()
        self.model.to(device)
        all_predictions = []

        with torch.no_grad():
            for start in range(0, len(texts), batch_size):
                batch_texts = texts[start:start+batch_size]
                encoded = self.tokenizer(batch_texts, padding=True, truncation=True, return_tensors='pt', max_length=256).to(device)

                outputs = self.model(**encoded)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)
                confidences, class_ids = torch.max(probs, dim=1)

                for i in range(len(batch_texts)):
                    class_id = class_ids[i].item()
                    confidence = confidences[i].item()
                    results = {
                        "class": self.label_names[class_id],
                        "confidence": confidence,
                        "class_id": class_id
                    }
                    all_predictions.append(results)


        return all_predictions
    
    def is_ready(self):
        if self.model != None and self.tokenizer != None:
            return True
        return False
    