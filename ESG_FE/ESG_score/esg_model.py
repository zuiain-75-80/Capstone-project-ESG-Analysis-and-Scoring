import torch
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification, 
    BertTokenizer, BertForSequenceClassification,
    DistilBertTokenizer, DistilBertForSequenceClassification,
    RobertaForSequenceClassification,
    XLMRobertaTokenizer, XLMRobertaForSequenceClassification,
    ElectraTokenizer, ElectraForSequenceClassification,
    DebertaV2ForSequenceClassification
)
from typing import Dict, List, Any
import os
import json

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

def detect_model_type(model_name: str) -> str:
    name = model_name.lower()
    for key in MODEL_MAP.keys():
        if key in name:
            return key
    return "auto"  # fallback


class ESGModel:
    def __init__(self, model_name: str, num_labels: int, category: str):
        self.model_name = model_name
        self.num_labels = num_labels
        self.category = category
        self.tokenizer = None
        self.model = None
        self.label_names = None
    
    def load_model(self, model_path: str):
        """Load model từ đường dẫn"""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model path không tồn tại: {model_path}")
        print(f"Loading model from: {model_path}")

        model_type = detect_model_type(model_path)
        ModelClass, TokenizerClass = MODEL_MAP[model_type]
        self.model = ModelClass.from_pretrained(model_path,
                        num_labels=self.num_labels, device_map="cuda"
                    )
        self.tokenizer = TokenizerClass.from_pretrained(model_path)
        
        # Load metadata
        metadata_path = os.path.join(model_path, 'model_metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                self.label_names = metadata.get('label_names', [])
                self.category = metadata.get('category', '')
        
        print(f"Model {self.category} đã được load thành công")
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
        )
        
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
    
    def batch_predict(self, texts: List[str], batch_size: int = 16) -> List[Dict[str, float]]:
        """Predict batch text"""
        if self.model is None or self.tokenizer is None:
            raise ValueError("Model chưa được khởi tạo hoặc load.")
        
        self.model.eval()
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            # Tokenize cho cả batch
            inputs = self.tokenizer(
                batch_texts,
                return_tensors='pt',
                truncation=True,
                padding=True,
                max_length=256
            ).to("cuda")

            with torch.no_grad():
                outputs = self.model(**inputs)
                probabilities = torch.softmax(outputs.logits, dim=-1)  # shape: (batch, num_classes)
                predicted_class_idxs = torch.argmax(probabilities, dim=-1)

            for idx, probs in zip(predicted_class_idxs, probabilities):
                results.append({
                    "class": self.label_names[idx.item()],
                    "confidence": probs[idx].item(),
                    "class_id": idx.item()
                })

        return results


