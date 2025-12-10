import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
from ESG_score.esg_model import ESGModel

import warnings
warnings.filterwarnings('ignore')

class ESGScoreCalculator:
    def __init__(self):
        """
        ESG Score Calculator cải tiến dựa trên SASB materiality map và sentiment analysis
        """
        self.industry_esg_weights = {
            'Communication Services (Services)': {
                'E': 0.75,
                'S': 2.0,
                'G': 0.75
            },
            'Telecommunication Services (Technology & Communications)': {
                'E': 1.5,
                'S': 2.75,
                'G': 2.75
            },
            'Industrials (Transportation)': {
                'E': 2.25,
                'S': 1.25,
                'G': 2.0
            },
            'Consumer Discretionary (Consumer Goods)': {
                'E': 0.5,
                'S': 1.75,
                'G': 1.75
            },
            'Materials (Extractives & Minerals Processing)': {
                'E': 4.0,
                'S': 1.25,
                'G': 2.25
            },
            'Financials': {
                'E': 0.0,
                'S': 1.75,
                'G': 1.75
            },
            'Consumer Staples (Food and Beverage)': {
                'E': 2.25,
                'S': 3.0,
                'G': 2.25
            },
            'Health Care': {
                'E': 0.75,
                'S': 4.25,
                'G': 1.5
            },
            'Utilities (Infrastructure)': {
                'E': 1.5,
                'S': 1.5,
                'G': 2.75
            },
            'Energy (Resource Transformation)': {
                'E': 2.25,
                'S': 1.5,
                'G': 2.5
            }
        }
        

    def classify_multiple_sentiment(self, df: pd.DataFrame, model_path: str):
        category_labels = {
            'environment': ['Environmental Negative', 'Environmental Neutral', 'Environmental Positive'],
            'governance': ['Governance Negative', 'Governance Neutral', 'Governance Positive'],
            'social': ['Social Negative', 'Social Neutral', 'Social Positive']
        }
        categories = ["environment", "governance", "social"]
        summary = {}
        for category in categories:
            texts = df[df["label"].str.lower() == category]["text"].tolist()
            if texts == []:
                continue
            labels = category_labels[category]
            result_df = self.classify_single_sentiment(texts, model_path + f"/{category}", category, labels)
            result_df.loc[result_df["confidence"] < 0.6, "label"] = labels[1]  # always use Neutral label

            label_counts = {
                "Positive": sum(result_df["label"] == labels[2]),
                "Neutral": sum(result_df["label"] == labels[1]),
                "Negative": sum(result_df["label"] == labels[0])
            }
            summary[category] = label_counts
        return summary

    def classify_single_sentiment(self, texts: List[str], model_path: str, category: str, labels: List[str]):
        """class sentiment"""
        model = ESGModel(
            model_name = model_path,
            num_labels = len(labels),
            category = category
        )
        model.load_model(model_path)
        results = model.batch_predict(texts) #List[Dict[str, float]
        data = []
        for text, result in zip(texts, results):
            label = result['class']
            confidence = result['confidence']
            data.append({
                "label": label,
                "confidence": confidence,
                "text": text
            })

        df = pd.DataFrame(data)
        return df

    def calculate_company_esg_score(self, 
                                   company_texts: pd.DataFrame, 
                                   industry: str,
                                   model_path: str) -> Dict[str, float]:
        """
        Tính điểm ESG theo công thức:
        ESG_company = W_E × (∑S_E,i/N_company) + W_S × (∑S_S,j/N_company) + W_G × (∑S_G,k/N_company)
        company_texts: DataFrame ["text", "label"]
        """
        
        if industry not in self.industry_esg_weights:
            available_industries = list(self.industry_esg_weights.keys())
            raise ValueError(f"Industry '{industry}' not supported. Available: {available_industries}")
        
        weights = self.industry_esg_weights[industry]
        summary = self.classify_multiple_sentiment(company_texts, model_path)

        # categories = ["environment", "governance", "social"]
        e_sentiment = (summary["environment"]["Positive"] if "environment" in summary else 0) - \
              (summary["environment"]["Negative"] if "environment" in summary else 0)

        g_sentiment = (summary["governance"]["Positive"] if "governance" in summary else 0) - \
                    (summary["governance"]["Negative"] if "governance" in summary else 0)

        s_sentiment = (summary["social"]["Positive"] if "social" in summary else 0) - \
                    (summary["social"]["Negative"] if "social" in summary else 0)

        # ESG Score theo công thức chính thức
        esg_score = (weights['E'] * e_sentiment + 
                    weights['G'] * g_sentiment  + 
                    weights['S'] * s_sentiment)
        
        sentiment_counts = []

        for category in ["environment", "social", "governance"]:
            sentiments = ["Positive", "Neutral", "Negative"]
            for sentiment in sentiments:
                count = summary.get(category, {}).get(sentiment, 0)
                sentiment_counts.append({
                    "ESG Category": category.capitalize(),
                    "Sentiment": sentiment,
                    "Count": count
                })

        sentiment_df = pd.DataFrame(sentiment_counts)
        
        return {
            'company_esg_score': esg_score,
            'weighted_e_contribution': weights['E'] * e_sentiment,
            'weighted_s_contribution': weights['S'] * s_sentiment, 
            'weighted_g_contribution': weights['G'] * g_sentiment,
            'e_sentiment_avg': e_sentiment,
            's_sentiment_avg': s_sentiment,
            'g_sentiment_avg': g_sentiment,
            'total_sentences': len(company_texts[company_texts["label"] != "Irrelevant"]["text"]),
            'industry_weights': weights.copy(),
            'sentiment_df': sentiment_df
        }
    
