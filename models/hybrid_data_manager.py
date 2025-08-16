# models/hybrid_data_manager.py
# 混合資料管理器 - 整合傳統SQL資料庫和向量資料庫

import os
# import logging  # 註解掉 logging 模組
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from datetime import datetime

# 導入現有的資料管理器和新的向量資料庫管理器
from .data_manager import DataManager
from .vector_database_manager import VectorDatabaseManager

class HybridDataManager:
    """
    混合資料管理器
    
    功能:
    1. 整合傳統SQL資料庫和向量資料庫
    2. 提供統一的資料存取介面
    3. 支援混合查詢 (SQL + 向量搜尋)
    4. 自動資料同步
    """
    
    def __init__(self, db_file: str):
        """
        初始化混合資料管理器
        
        Args:
            db_file: SQLite 資料庫檔案路徑
        """
        # self.logger = logging.getLogger(__name__)  # 註解掉 logger
        
        # 初始化傳統資料管理器
        self.sql_manager = DataManager(db_file)
        # self.logger.info("SQL 資料管理器初始化完成")  # 註解掉 logging
        
        # 初始化向量資料庫管理器
        self.vector_manager = VectorDatabaseManager()
        # self.logger.info("向量資料庫管理器初始化完成")  # 註解掉 logging
        
        # 執行初始資料同步
        try:
            self._sync_data_to_vector_db()
            # self.logger.info("向量資料庫同步完成")  # 註解掉 logging
        except Exception as e:
            # self.logger.error(f"向量資料庫同步失敗: {e}")  # 註解掉 logging
            # 即使同步失敗，也要確保基本功能可用
            # self.logger.warning("將以基本模式運行，向量功能可能受限")  # 註解掉 logging
            pass
    
    def _sync_data_to_vector_db(self):
        """同步SQL資料庫的資料到向量資料庫"""
        try:
            # self.logger.info("開始同步資料到向量資料庫...")  # 註解掉 logging
            
            # 同步產品資料
            self._sync_products()
            
            # 同步客戶資料
            self._sync_customers()
            
            # 同步銷售事件資料
            self._sync_sales_events()
            
            # self.logger.info("資料同步完成")  # 註解掉 logging
            
        except Exception as e:
            # self.logger.error(f"資料同步失敗: {e}")  # 註解掉 logging
            pass
    
    def _sync_products(self):
        """同步產品資料"""
        try:
            # 從SQL資料庫獲取產品資料
            products_query = "SELECT * FROM dim_product"
            products_df = self.sql_manager.execute_query(products_query)
            
            if not products_df.empty:
                # 向量化產品資料
                product_points = self.vector_manager.vectorize_products(products_df)
                
                # 插入到向量資料庫
                success = self.vector_manager.insert_vectors("products", product_points)
                
                if success:
                    # self.logger.info(f"成功同步 {len(product_points)} 個產品到向量資料庫")  # 註解掉 logging
                    pass
                else:
                    # self.logger.error("產品資料同步失敗")  # 註解掉 logging
                    pass
            
        except Exception as e:
            # self.logger.error(f"產品資料同步失敗: {e}")  # 註解掉 logging
            pass
    
    def _sync_customers(self):
        """同步客戶資料"""
        try:
            # 從SQL資料庫獲取客戶資料
            customers_query = "SELECT * FROM dim_customer"
            customers_df = self.sql_manager.execute_query(customers_query)
            
            if not customers_df.empty:
                # 向量化客戶資料
                customer_points = self.vector_manager.vectorize_customers(customers_df)
                
                # 插入到向量資料庫
                success = self.vector_manager.insert_vectors("customers", customer_points)
                
                if success:
                    # self.logger.info(f"成功同步 {len(customer_points)} 個客戶到向量資料庫")  # 註解掉 logging
                    pass
                else:
                    # self.logger.error("客戶資料同步失敗")  # 註解掉 logging
                    pass
            
        except Exception as e:
            # self.logger.error(f"客戶資料同步失敗: {e}")  # 註解掉 logging
            pass
    
    def _sync_sales_events(self):
        """同步銷售事件資料"""
        try:
            # 從SQL資料庫獲取完整的銷售事件資料
            # 移除 LIMIT 1000 限制，同步完整數據
            sales_query = """
                SELECT f.*, 
                       p.product_name, p.category, p.brand,
                       c.customer_name, c.gender, c.age, c.loyalty_level,
                       s.staff_name, s.title,
                       r.region_name, r.country, r.city,
                       t.date, t.month, t.quarter, t.year
                FROM sales_fact f
                JOIN dim_product p ON f.product_id = p.product_id
                JOIN dim_customer c ON f.customer_id = c.customer_id
                JOIN dim_staff s ON f.staff_id = s.staff_id
                JOIN dim_region r ON f.region_id = r.region_id
                JOIN dim_time t ON f.time_id = t.time_id
                ORDER BY t.date DESC
            """
            sales_df = self.sql_manager.execute_query(sales_query)
            
            if not sales_df.empty:
                # 向量化銷售事件資料
                sales_points = self.vector_manager.vectorize_sales_events(sales_df)
                
                # 插入到向量資料庫
                success = self.vector_manager.insert_vectors("sales_events", sales_points)
                
                if success:
                    # self.logger.info(f"成功同步 {len(sales_points)} 個銷售事件到向量資料庫")  # 註解掉 logging
                    # self.logger.info(f"數據時間範圍：{sales_df['date'].min()} 到 {sales_df['date'].max()}")  # 註解掉 logging
                    pass
                else:
                    # self.logger.error("銷售事件資料同步失敗")  # 註解掉 logging
                    pass
            else:
                # self.logger.warning("沒有找到銷售事件數據")  # 註解掉 logging
                pass
            
        except Exception as e:
            # self.logger.error(f"銷售事件資料同步失敗: {e}")  # 註解掉 logging
            pass
    
    # ==================== 傳統SQL查詢方法 (保持向後相容) ====================
    
    def execute_query(self, query: str, params=()) -> pd.DataFrame:
        """執行SQL查詢 (向後相容)"""
        return self.sql_manager.execute_query(query, params)
    
    def get_period_comparison(self, current_start, current_end, last_start, last_end):
        """期間比較分析 (向後相容)"""
        return self.sql_manager.get_period_comparison(
            current_start, current_end, last_start, last_end
        )
    
    def get_driver_analysis(self, current_start, current_end, last_start, last_end, dimension='product'):
        """貢獻度分析 (向後相容)"""
        return self.sql_manager.get_driver_analysis(
            current_start, current_end, last_start, last_end, dimension
        )
    
    def get_drill_down_analysis(self, current_start, current_end, last_start, last_end, 
                               primary_dimension, primary_value, drill_dimension):
        """下鑽分析 (向後相容)"""
        return self.sql_manager.get_drill_down_analysis(
            current_start, current_end, last_start, last_end,
            primary_dimension, primary_value, drill_dimension
        )
    
    def get_all_tables(self):
        """獲取所有資料表 (向後相容)"""
        return self.sql_manager.get_all_tables()
    
    def get_table_schema(self, table_name: str):
        """獲取資料表結構 (向後相容)"""
        return self.sql_manager.get_table_schema(table_name)
    
    def get_table_data(self, table_name: str, page=1, limit=10):
        """獲取資料表資料 (向後相容)"""
        return self.sql_manager.get_table_data(table_name, page, limit)
    
    def execute_custom_sql(self, sql_query: str):
        """執行自定義SQL查詢 (向後相容)"""
        return self.sql_manager.execute_custom_sql(sql_query)
    
    # ==================== 新增向量搜尋方法 ====================
    
    def search_similar_products(self, query_text: str, limit: int = 10) -> Dict[str, Any]:
        """
        搜尋相似產品
        
        Args:
            query_text: 查詢文字 (產品名稱、類別、品牌等)
            limit: 返回結果數量
            
        Returns:
            搜尋結果字典
        """
        try:
            # 執行向量相似性搜尋
            vector_results = self.vector_manager.search_similar_products(query_text, limit)
            
            # 如果有結果，從SQL資料庫獲取完整資訊
            if vector_results:
                product_ids = [str(r["product_id"]) for r in vector_results]
                sql_query = f"""
                    SELECT p.*, 
                           COALESCE(SUM(f.amount), 0) as total_sales,
                           COALESCE(SUM(f.quantity), 0) as total_quantity
                    FROM dim_product p
                    LEFT JOIN sales_fact f ON p.product_id = f.product_id
                    WHERE p.product_id IN ({','.join(product_ids)})
                    GROUP BY p.product_id, p.product_name, p.category, p.brand
                """
                
                sql_results = self.sql_manager.execute_query(sql_query)
                
                # 合併向量搜尋結果和SQL查詢結果
                enhanced_results = []
                for vector_result in vector_results:
                    product_id = vector_result["product_id"]
                    sql_row = sql_results[sql_results["product_id"] == product_id]
                    
                    if not sql_row.empty:
                        enhanced_result = {
                            **vector_result,
                            "total_sales": float(sql_row.iloc[0]["total_sales"]),
                            "total_quantity": int(sql_row.iloc[0]["total_quantity"])
                        }
                        enhanced_results.append(enhanced_result)
                
                return {
                    "success": True,
                    "query": query_text,
                    "results": enhanced_results,
                    "count": len(enhanced_results)
                }
            else:
                return {
                    "success": True,
                    "query": query_text,
                    "results": [],
                    "count": 0,
                    "message": "未找到相似產品"
                }
                
        except Exception as e:
            # self.logger.error(f"產品相似性搜尋失敗: {e}")  # 註解掉 logging
            return {
                "success": False,
                "error": str(e)
            }
    
    def search_similar_customers(self, query_text: str, limit: int = 10) -> Dict[str, Any]:
        """
        搜尋相似客戶
        
        Args:
            query_text: 查詢文字 (客戶名稱、性別、忠誠度等)
            limit: 返回結果數量
            
        Returns:
            搜尋結果字典
        """
        try:
            # 執行向量相似性搜尋
            vector_results = self.vector_manager.search_similar_customers(query_text, limit)
            
            # 如果有結果，從SQL資料庫獲取完整資訊
            if vector_results:
                customer_ids = [str(r["customer_id"]) for r in vector_results]
                sql_query = f"""
                    SELECT c.*, 
                           COALESCE(SUM(f.amount), 0) as total_purchases,
                           COALESCE(COUNT(f.sale_id), 0) as purchase_count
                    FROM dim_customer c
                    LEFT JOIN sales_fact f ON c.customer_id = f.customer_id
                    WHERE c.customer_id IN ({','.join(customer_ids)})
                    GROUP BY c.customer_id, c.customer_name, c.gender, c.age, c.loyalty_level
                """
                
                sql_results = self.sql_manager.execute_query(sql_query)
                
                # 合併向量搜尋結果和SQL查詢結果
                enhanced_results = []
                for vector_result in vector_results:
                    customer_id = vector_result["customer_id"]
                    sql_row = sql_results[sql_results["customer_id"] == customer_id]
                    
                    if not sql_row.empty:
                        enhanced_result = {
                            **vector_result,
                            "total_purchases": float(sql_row.iloc[0]["total_purchases"]),
                            "purchase_count": int(sql_row.iloc[0]["purchase_count"])
                        }
                        enhanced_results.append(enhanced_result)
                
                return {
                    "success": True,
                    "query": query_text,
                    "results": enhanced_results,
                    "count": len(enhanced_results)
                }
            else:
                return {
                    "success": True,
                    "query": query_text,
                    "results": [],
                    "count": 0,
                    "message": "未找到相似客戶"
                }
                
        except Exception as e:
            # self.logger.error(f"客戶相似性搜尋失敗: {e}")  # 註解掉 logging
            return {
                "success": False,
                "error": str(e)
            }
    
    def search_similar_sales(self, quantity: float, amount: float, 
                           limit: int = 10) -> Dict[str, Any]:
        """
        搜尋相似銷售事件
        
        Args:
            quantity: 數量
            amount: 金額
            limit: 返回結果數量
            
        Returns:
            搜尋結果字典
        """
        try:
            # 執行向量相似性搜尋
            vector_results = self.vector_manager.search_similar_sales(quantity, amount, limit)
            
            # 如果有結果，從SQL資料庫獲取完整資訊
            if vector_results:
                sale_ids = [str(r["sale_id"]) for r in vector_results]
                sql_query = f"""
                    SELECT f.*, p.product_name, c.customer_name, s.staff_name, r.region_name, t.date
                    FROM sales_fact f
                    JOIN dim_product p ON f.product_id = p.product_id
                    JOIN dim_customer c ON f.customer_id = c.customer_id
                    JOIN dim_staff s ON f.staff_id = s.staff_id
                    JOIN dim_region r ON f.region_id = r.region_id
                    JOIN dim_time t ON f.time_id = t.time_id
                    WHERE f.sale_id IN ({','.join(sale_ids)})
                """
                
                sql_results = self.sql_manager.execute_query(sql_query)
                
                # 合併向量搜尋結果和SQL查詢結果
                enhanced_results = []
                for vector_result in vector_results:
                    sale_id = vector_result["sale_id"]
                    sql_row = sql_results[sql_results["sale_id"] == sale_id]
                    
                    if not sql_row.empty:
                        enhanced_result = {
                            **vector_result,
                            "product_name": str(sql_row.iloc[0]["product_name"]),
                            "customer_name": str(sql_row.iloc[0]["customer_name"]),
                            "staff_name": str(sql_row.iloc[0]["staff_name"]),
                            "region_name": str(sql_row.iloc[0]["region_name"]),
                            "date": str(sql_row.iloc[0]["date"])
                        }
                        enhanced_results.append(enhanced_result)
                
                return {
                    "success": True,
                    "query": f"數量: {quantity}, 金額: {amount}",
                    "results": enhanced_results,
                    "count": len(enhanced_results)
                }
            else:
                return {
                    "success": True,
                    "query": f"數量: {quantity}, 金額: {amount}",
                    "results": [],
                    "count": 0,
                    "message": "未找到相似銷售事件"
                }
                
        except Exception as e:
            # self.logger.error(f"銷售事件相似性搜尋失敗: {e}")  # 註解掉 logging
            return {
                "success": False,
                "error": str(e)
            }
    
    def recommend_products_for_customer(self, customer_id: int, limit: int = 5) -> Dict[str, Any]:
        """
        為客戶推薦產品
        
        Args:
            customer_id: 客戶ID
            limit: 推薦產品數量
            
        Returns:
            推薦結果字典
        """
        try:
            # 獲取客戶資訊
            customer_query = f"SELECT * FROM dim_customer WHERE customer_id = {customer_id}"
            customer_df = self.sql_manager.execute_query(customer_query)
            
            if customer_df.empty:
                return {
                    "success": False,
                    "error": f"客戶 ID {customer_id} 不存在"
                }
            
            customer_info = customer_df.iloc[0]
            
            # 獲取客戶購買歷史
            purchase_query = f"""
                SELECT p.product_name, p.category, p.brand, SUM(f.amount) as total_spent
                FROM sales_fact f
                JOIN dim_product p ON f.product_id = p.product_id
                WHERE f.customer_id = {customer_id}
                GROUP BY p.product_id, p.product_name, p.category, p.brand
                ORDER BY total_spent DESC
            """
            purchase_history = self.sql_manager.execute_query(purchase_query)
            
            # 基於客戶特徵和購買歷史生成查詢文字
            if not purchase_history.empty:
                # 使用最常購買的類別和品牌
                top_category = purchase_history.iloc[0]["category"]
                top_brand = purchase_history.iloc[0]["brand"]
                query_text = f"{customer_info['loyalty_level']} {customer_info['gender']} {top_category} {top_brand}"
            else:
                # 如果沒有購買歷史，使用客戶基本特徵
                query_text = f"{customer_info['loyalty_level']} {customer_info['gender']}"
            
            # 搜尋相似產品
            similar_products = self.search_similar_products(query_text, limit * 2)
            
            if similar_products["success"] and similar_products["results"]:
                # 過濾掉客戶已購買的產品
                purchased_products = set(purchase_history["product_name"].tolist()) if not purchase_history.empty else set()
                
                recommendations = []
                for product in similar_products["results"]:
                    if product["product_name"] not in purchased_products and len(recommendations) < limit:
                        recommendations.append(product)
                
                return {
                    "success": True,
                    "customer_id": customer_id,
                    "customer_name": customer_info["customer_name"],
                    "recommendations": recommendations,
                    "count": len(recommendations)
                }
            else:
                return {
                    "success": True,
                    "customer_id": customer_id,
                    "customer_name": customer_info["customer_name"],
                    "recommendations": [],
                    "count": 0,
                    "message": "暫無推薦產品"
                }
                
        except Exception as e:
            # self.logger.error(f"產品推薦失敗: {e}")  # 註解掉 logging
            return {
                "success": False,
                "error": str(e)
            }
    
    def detect_sales_anomalies(self, threshold_score: float = 0.3, limit: int = 20) -> Dict[str, Any]:
        """
        檢測銷售異常
        
        Args:
            threshold_score: 異常分數閾值
            limit: 返回結果數量
            
        Returns:
            異常檢測結果字典
        """
        try:
            # 獲取最近的銷售資料
            recent_sales_query = """
                SELECT f.*, p.product_name, c.customer_name, t.date
                FROM sales_fact f
                JOIN dim_product p ON f.product_id = p.product_id
                JOIN dim_customer c ON f.customer_id = c.customer_id
                JOIN dim_time t ON f.time_id = t.time_id
                ORDER BY f.sale_id DESC
                LIMIT 100
            """
            recent_sales = self.sql_manager.execute_query(recent_sales_query)
            
            if recent_sales.empty:
                return {
                    "success": True,
                    "anomalies": [],
                    "count": 0,
                    "message": "無銷售資料"
                }
            
            anomalies = []
            
            # 對每筆銷售進行異常檢測
            for _, sale in recent_sales.iterrows():
                # 搜尋相似的銷售事件
                similar_sales = self.search_similar_sales(
                    sale["quantity"], 
                    sale["amount"], 
                    limit=5
                )
                
                if similar_sales["success"] and similar_sales["results"]:
                    # 計算最高相似度分數
                    max_score = max([r["score"] for r in similar_sales["results"]])
                    
                    # 如果相似度分數低於閾值，視為異常
                    if max_score < threshold_score:
                        anomaly = {
                            "sale_id": sale["sale_id"],
                            "product_name": sale["product_name"],
                            "customer_name": sale["customer_name"],
                            "quantity": sale["quantity"],
                            "amount": sale["amount"],
                            "date": sale["date"],
                            "anomaly_score": 1 - max_score,  # 異常分數 = 1 - 最高相似度
                            "reason": "銷售模式異常"
                        }
                        anomalies.append(anomaly)
            
            # 按異常分數排序
            anomalies.sort(key=lambda x: x["anomaly_score"], reverse=True)
            
            return {
                "success": True,
                "anomalies": anomalies[:limit],
                "count": len(anomalies[:limit]),
                "threshold": threshold_score
            }
            
        except Exception as e:
            # self.logger.error(f"異常檢測失敗: {e}")  # 註解掉 logging
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_available_dimensions(self, current_dimension):
        """獲取可用的維度 (向後相容)"""
        return self.sql_manager.get_available_dimensions(current_dimension)
    
    def get_quarter_comparison(self, current_year, current_quarter, compare_year, compare_quarter):
        """季度比較分析 (向後相容)"""
        return self.sql_manager.get_quarter_comparison(
            current_year, current_quarter, compare_year, compare_quarter
        )
    
    def get_quarter_driver_analysis(self, year, quarter, dimension='product'):
        """季度貢獻度分析 (向後相容)"""
        return self.sql_manager.get_quarter_driver_analysis(year, quarter, dimension)
    
    def get_vector_database_status(self) -> Dict[str, Any]:
        """
        獲取向量資料庫狀態
        
        Returns:
            狀態資訊字典
        """
        try:
            status = {
                "collections": {}
            }
            
            for collection_name in self.vector_manager.collections_config.keys():
                collection_info = self.vector_manager.get_collection_info(collection_name)
                status["collections"][collection_name] = collection_info
            
            return {
                "success": True,
                "status": status
            }
            
        except Exception as e:
            # self.logger.error(f"獲取向量資料庫狀態失敗: {e}")  # 註解掉 logging
            return {
                "success": False,
                "error": str(e)
            }
    
    def refresh_vector_database(self) -> Dict[str, Any]:
        """
        重新整理向量資料庫
        
        Returns:
            操作結果字典
        """
        try:
            # 清空所有集合
            for collection_name in self.vector_manager.collections_config.keys():
                self.vector_manager.clear_collection(collection_name)
            
            # 重新同步資料
            self._sync_data_to_vector_db()
            
            return {
                "success": True,
                "message": "向量資料庫重新整理完成"
            }
            
        except Exception as e:
            # self.logger.error(f"向量資料庫重新整理失敗: {e}")  # 註解掉 logging
            return {
                "success": False,
                "error": str(e)
            }

