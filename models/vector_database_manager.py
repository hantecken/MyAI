# models/vector_database_manager.py
# 向量資料庫管理器 - 負責向量資料的儲存、索引和搜尋

import os
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
# import logging  # 註解掉 logging 模組

# 向量資料庫相關套件
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, 
    MatchValue, SearchRequest, CollectionInfo, UpdateResult
)
from sentence_transformers import SentenceTransformer

# 數據處理套件
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.decomposition import PCA

class VectorDatabaseManager:
    """
    向量資料庫管理器
    
    功能:
    1. 向量化數據 (文字、數值、類別)
    2. 向量儲存和索引
    3. 相似性搜尋
    4. 混合查詢 (結合傳統SQL和向量搜尋)
    """
    
    def __init__(self, qdrant_host="localhost", qdrant_port=6333, 
                 embedding_model="all-MiniLM-L6-v2"):
        """
        初始化向量資料庫管理器
        
        Args:
            qdrant_host: Qdrant 服務器主機
            qdrant_port: Qdrant 服務器端口
            embedding_model: 文字嵌入模型名稱
        """
        # self.logger = logging.getLogger(__name__)  # 註解掉 logger
        
        # 初始化 Qdrant 客戶端 (使用內存模式進行開發)
        try:
            self.qdrant_client = QdrantClient(":memory:")  # 使用內存模式
            # self.logger.info("Qdrant 客戶端初始化成功 (內存模式)")  # 註解掉 logging
        except Exception as e:
            # self.logger.error(f"Qdrant 客戶端初始化失敗: {e}")  # 註解掉 logging
            raise
        
        # 初始化文字嵌入模型
        try:
            # 嘗試載入指定的模型
            self.text_encoder = SentenceTransformer(embedding_model)
            # self.logger.info(f"文字嵌入模型載入成功: {embedding_model}")  # 註解掉 logging
        except Exception as e:
            # self.logger.warning(f"指定模型載入失敗: {e}")  # 註解掉 logging
            try:
                # 嘗試載入預設模型
                self.text_encoder = SentenceTransformer("all-MiniLM-L6-v2")
                # self.logger.info("預設文字嵌入模型載入成功")  # 註解掉 logging
            except Exception as e2:
                # self.logger.warning(f"預設模型載入失敗: {e2}")  # 註解掉 logging
                try:
                    # 嘗試載入最輕量的模型
                    self.text_encoder = SentenceTransformer("paraphrase-MiniLM-L3-v2")
                    # self.logger.info("輕量文字嵌入模型載入成功")  # 註解掉 logging
                except Exception as e3:
                    # self.logger.error(f"所有文字嵌入模型載入失敗: {e3}")  # 註解掉 logging
                    raise
        
        # 初始化數值處理器
        self.numerical_scaler = StandardScaler()
        self.label_encoders = {}
        self.pca_reducers = {}
        
        # 集合配置
        self.collections_config = {
            "products": {
                "vector_size": 384,  # all-MiniLM-L6-v2 的向量維度
                "distance": Distance.COSINE
            },
            "customers": {
                "vector_size": 384,
                "distance": Distance.COSINE
            },
            "sales_events": {
                "vector_size": 128,  # 較小的維度用於數值特徵
                "distance": Distance.EUCLID
            },
            "time_series": {
                "vector_size": 64,
                "distance": Distance.EUCLID
            }
        }
        
        # 初始化集合
        self._initialize_collections()
    
    def _initialize_collections(self):
        """初始化所有向量集合"""
        for collection_name, config in self.collections_config.items():
            try:
                # 檢查集合是否已存在
                collections = self.qdrant_client.get_collections().collections
                existing_collections = [c.name for c in collections]
                
                if collection_name not in existing_collections:
                    self.qdrant_client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=config["vector_size"],
                            distance=config["distance"]
                        )
                    )
                    # self.logger.info(f"集合 '{collection_name}' 創建成功")  # 註解掉 logging
                else:
                    # self.logger.info(f"集合 '{collection_name}' 已存在")  # 註解掉 logging
                    pass
                    
            except Exception as e:
                # self.logger.error(f"集合 '{collection_name}' 初始化失敗: {e}")  # 註解掉 logging
                pass
    
    def encode_text(self, texts: List[str]) -> np.ndarray:
        """
        將文字轉換為向量
        
        Args:
            texts: 文字列表
            
        Returns:
            向量陣列
        """
        try:
            if not texts:
                return np.array([])
            
            # 處理空值
            processed_texts = [str(text) if text is not None else "" for text in texts]
            
            # 生成嵌入向量
            embeddings = self.text_encoder.encode(processed_texts)
            return embeddings
            
        except Exception as e:
            # self.logger.error(f"文字編碼失敗: {e}")  # 註解掉 logging
            raise
    
    def encode_numerical(self, data: np.ndarray, collection_name: str, 
                        fit: bool = False) -> np.ndarray:
        """
        將數值數據轉換為向量
        
        Args:
            data: 數值數據陣列
            collection_name: 集合名稱
            fit: 是否訓練標準化器
            
        Returns:
            標準化後的向量陣列
        """
        try:
            if data.size == 0:
                return np.array([])
            
            # 確保數據是二維的
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            
            scaler_key = f"{collection_name}_numerical"
            
            if fit or scaler_key not in self.label_encoders:
                # 訓練標準化器
                if scaler_key not in self.label_encoders:
                    self.label_encoders[scaler_key] = StandardScaler()
                
                scaled_data = self.label_encoders[scaler_key].fit_transform(data)
            else:
                # 使用已訓練的標準化器
                scaled_data = self.label_encoders[scaler_key].transform(data)
            
            # 如果維度過高，使用 PCA 降維
            target_dim = self.collections_config[collection_name]["vector_size"]
            if scaled_data.shape[1] > target_dim:
                pca_key = f"{collection_name}_pca"
                
                if fit or pca_key not in self.pca_reducers:
                    if pca_key not in self.pca_reducers:
                        self.pca_reducers[pca_key] = PCA(n_components=target_dim)
                    
                    scaled_data = self.pca_reducers[pca_key].fit_transform(scaled_data)
                else:
                    scaled_data = self.pca_reducers[pca_key].transform(scaled_data)
            
            return scaled_data
            
        except Exception as e:
            # self.logger.error(f"數值編碼失敗: {e}")  # 註解掉 logging
            raise
    
    def encode_categorical(self, categories: List[str], collection_name: str,
                          fit: bool = False) -> np.ndarray:
        """
        將類別數據轉換為向量
        
        Args:
            categories: 類別列表
            collection_name: 集合名稱
            fit: 是否訓練編碼器
            
        Returns:
            編碼後的向量陣列
        """
        try:
            if not categories:
                return np.array([])
            
            encoder_key = f"{collection_name}_categorical"
            
            if fit or encoder_key not in self.label_encoders:
                if encoder_key not in self.label_encoders:
                    self.label_encoders[encoder_key] = LabelEncoder()
                
                encoded = self.label_encoders[encoder_key].fit_transform(categories)
            else:
                encoded = self.label_encoders[encoder_key].transform(categories)
            
            # 轉換為 one-hot 編碼
            n_classes = len(self.label_encoders[encoder_key].classes_)
            one_hot = np.eye(n_classes)[encoded]
            
            return one_hot
            
        except Exception as e:
            # self.logger.error(f"類別編碼失敗: {e}")  # 註解掉 logging
            raise
    
    def vectorize_products(self, products_df: pd.DataFrame) -> List[PointStruct]:
        """
        向量化產品數據
        
        Args:
            products_df: 產品數據框
            
        Returns:
            向量點列表
        """
        try:
            points = []
            
            for idx, row in products_df.iterrows():
                # 組合文字特徵
                text_features = f"{row['product_name']} {row['category']} {row['brand']}"
                
                # 生成文字嵌入
                text_vector = self.encode_text([text_features])[0]
                
                # 創建向量點
                point = PointStruct(
                    id=int(row['product_id']),
                    vector=text_vector.tolist(),
                    payload={
                        "product_id": int(row['product_id']),
                        "product_name": str(row['product_name']),
                        "category": str(row['category']),
                        "brand": str(row['brand']),
                        "type": "product"
                    }
                )
                points.append(point)
            
            return points
            
        except Exception as e:
            # self.logger.error(f"產品向量化失敗: {e}")  # 註解掉 logging
            raise
    
    def vectorize_customers(self, customers_df: pd.DataFrame) -> List[PointStruct]:
        """
        向量化客戶數據
        
        Args:
            customers_df: 客戶數據框
            
        Returns:
            向量點列表
        """
        try:
            points = []
            
            for idx, row in customers_df.iterrows():
                # 組合文字特徵
                text_features = f"{row['customer_name']} {row['gender']} {row['loyalty_level']}"
                
                # 生成文字嵌入
                text_vector = self.encode_text([text_features])[0]
                
                # 創建向量點
                point = PointStruct(
                    id=int(row['customer_id']),
                    vector=text_vector.tolist(),
                    payload={
                        "customer_id": int(row['customer_id']),
                        "customer_name": str(row['customer_name']),
                        "gender": str(row['gender']),
                        "age": int(row['age']),
                        "loyalty_level": str(row['loyalty_level']),
                        "type": "customer"
                    }
                )
                points.append(point)
            
            return points
            
        except Exception as e:
            # self.logger.error(f"客戶向量化失敗: {e}")  # 註解掉 logging
            raise
    
    def vectorize_sales_events(self, sales_df: pd.DataFrame) -> List[PointStruct]:
        """
        向量化銷售事件數據
        
        Args:
            sales_df: 銷售數據框
            
        Returns:
            向量點列表
        """
        try:
            points = []
            
            # 準備數值特徵
            numerical_features = sales_df[['quantity', 'amount']].values
            
            # 標準化數值特徵
            scaled_features = self.encode_numerical(
                numerical_features, 
                "sales_events", 
                fit=True
            )
            
            # 如果維度不足，進行填充
            target_dim = self.collections_config["sales_events"]["vector_size"]
            if scaled_features.shape[1] < target_dim:
                padding = np.zeros((scaled_features.shape[0], 
                                  target_dim - scaled_features.shape[1]))
                scaled_features = np.hstack([scaled_features, padding])
            
            for idx, row in sales_df.iterrows():
                # 創建向量點
                point = PointStruct(
                    id=int(row['sale_id']),
                    vector=scaled_features[idx].tolist(),
                    payload={
                        "sale_id": int(row['sale_id']),
                        "product_id": int(row['product_id']),
                        "customer_id": int(row['customer_id']),
                        "staff_id": int(row['staff_id']),
                        "region_id": int(row['region_id']),
                        "time_id": int(row['time_id']),
                        "quantity": float(row['quantity']),
                        "amount": float(row['amount']),
                        "type": "sales_event"
                    }
                )
                points.append(point)
            
            return points
            
        except Exception as e:
            # self.logger.error(f"銷售事件向量化失敗: {e}")  # 註解掉 logging
            raise
    
    def insert_vectors(self, collection_name: str, points: List[PointStruct]) -> bool:
        """
        插入向量到指定集合
        
        Args:
            collection_name: 集合名稱
            points: 向量點列表
            
        Returns:
            是否成功
        """
        try:
            if not points:
                # self.logger.warning(f"沒有向量點需要插入到集合 '{collection_name}'")  # 註解掉 logging
                return True
            
            # 批量插入向量
            result = self.qdrant_client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            # self.logger.info(f"成功插入 {len(points)} 個向量到集合 '{collection_name}'")  # 註解掉 logging
            return True
            
        except Exception as e:
            # self.logger.error(f"向量插入失敗: {e}")  # 註解掉 logging
            return False
    
    def search_similar_products(self, query_text: str, limit: int = 10) -> List[Dict]:
        """
        搜尋相似產品
        
        Args:
            query_text: 查詢文字
            limit: 返回結果數量
            
        Returns:
            相似產品列表
        """
        try:
            # 生成查詢向量
            query_vector = self.encode_text([query_text])[0]
            
            # 執行相似性搜尋
            search_result = self.qdrant_client.search(
                collection_name="products",
                query_vector=query_vector.tolist(),
                limit=limit
            )
            
            # 格式化結果
            results = []
            for hit in search_result:
                result = {
                    "score": hit.score,
                    "product_id": hit.payload["product_id"],
                    "product_name": hit.payload["product_name"],
                    "category": hit.payload["category"],
                    "brand": hit.payload["brand"]
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            # self.logger.error(f"產品相似性搜尋失敗: {e}")  # 註解掉 logging
            return []
    
    def search_similar_customers(self, query_text: str, limit: int = 10) -> List[Dict]:
        """
        搜尋相似客戶
        
        Args:
            query_text: 查詢文字
            limit: 返回結果數量
            
        Returns:
            相似客戶列表
        """
        try:
            # 生成查詢向量
            query_vector = self.encode_text([query_text])[0]
            
            # 執行相似性搜尋
            search_result = self.qdrant_client.search(
                collection_name="customers",
                query_vector=query_vector.tolist(),
                limit=limit
            )
            
            # 格式化結果
            results = []
            for hit in search_result:
                result = {
                    "score": hit.score,
                    "customer_id": hit.payload["customer_id"],
                    "customer_name": hit.payload["customer_name"],
                    "gender": hit.payload["gender"],
                    "age": hit.payload["age"],
                    "loyalty_level": hit.payload["loyalty_level"]
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            # self.logger.error(f"客戶相似性搜尋失敗: {e}")  # 註解掉 logging
            return []
    
    def search_similar_sales(self, quantity: float, amount: float, 
                           limit: int = 10) -> List[Dict]:
        """
        搜尋相似銷售事件
        
        Args:
            quantity: 數量
            amount: 金額
            limit: 返回結果數量
            
        Returns:
            相似銷售事件列表
        """
        try:
            # 準備查詢向量
            query_features = np.array([[quantity, amount]])
            query_vector = self.encode_numerical(query_features, "sales_events")[0]
            
            # 如果維度不足，進行填充
            target_dim = self.collections_config["sales_events"]["vector_size"]
            if len(query_vector) < target_dim:
                padding = np.zeros(target_dim - len(query_vector))
                query_vector = np.hstack([query_vector, padding])
            
            # 執行相似性搜尋
            search_result = self.qdrant_client.search(
                collection_name="sales_events",
                query_vector=query_vector.tolist(),
                limit=limit
            )
            
            # 格式化結果
            results = []
            for hit in search_result:
                result = {
                    "score": hit.score,
                    "sale_id": hit.payload["sale_id"],
                    "product_id": hit.payload["product_id"],
                    "customer_id": hit.payload["customer_id"],
                    "quantity": hit.payload["quantity"],
                    "amount": hit.payload["amount"]
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            # self.logger.error(f"銷售事件相似性搜尋失敗: {e}")  # 註解掉 logging
            return []
    
    def get_collection_info(self, collection_name: str) -> Dict:
        """
        獲取集合資訊
        
        Args:
            collection_name: 集合名稱
            
        Returns:
            集合資訊字典
        """
        try:
            info = self.qdrant_client.get_collection(collection_name)
            
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "config": {
                    "vector_size": info.config.params.vectors.size,
                    "distance": info.config.params.vectors.distance.value
                }
            }
            
        except Exception as e:
            # self.logger.error(f"獲取集合資訊失敗: {e}")  # 註解掉 logging
            return {}
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        刪除集合
        
        Args:
            collection_name: 集合名稱
            
        Returns:
            是否成功
        """
        try:
            self.qdrant_client.delete_collection(collection_name)
            # self.logger.info(f"集合 '{collection_name}' 刪除成功")  # 註解掉 logging
            return True
            
        except Exception as e:
            # self.logger.error(f"集合刪除失敗: {e}")  # 註解掉 logging
            return False
    
    def clear_collection(self, collection_name: str) -> bool:
        """
        清空集合
        
        Args:
            collection_name: 集合名稱
            
        Returns:
            是否成功
        """
        try:
            # 刪除所有點
            self.qdrant_client.delete(
                collection_name=collection_name,
                points_selector=Filter()  # 空過濾器表示刪除所有點
            )
            
            # self.logger.info(f"集合 '{collection_name}' 清空成功")  # 註解掉 logging
            return True
            
        except Exception as e:
            # self.logger.error(f"集合清空失敗: {e}")  # 註解掉 logging
            return False

