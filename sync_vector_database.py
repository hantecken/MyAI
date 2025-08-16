#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量資料庫同步腳本
重新同步 SQLite 資料庫中的完整數據到向量資料庫
"""

import os
import sys
import logging
from datetime import datetime

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 導入必要的模組
from models.hybrid_data_manager import HybridDataManager

# def setup_logging():
#     """設定日誌"""
#     logging.basicConfig(
#         level=logging.INFO,
#         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#         handlers=[
#             logging.StreamHandler(),
#             logging.FileHandler('vector_sync.log', encoding='utf-8')
#         ]
#     )
#     return logging.getLogger(__name__)

def check_database_status(hybrid_manager):
    """檢查資料庫狀態"""
    # logger = logging.getLogger(__name__)  # 註解掉 logger
    
    # logger.info("🔍 檢查資料庫狀態...")  # 註解掉 logging
    
    try:
        # 檢查 SQLite 資料庫狀態
        # logger.info("📊 檢查 SQLite 資料庫...")  # 註解掉 logging
        
        # 檢查時間維度數據
        time_query = """
            SELECT 
                substr(date, 1, 4) as year,
                COUNT(DISTINCT substr(date, 1, 7)) as months,
                COUNT(*) as total_records,
                MIN(date) as earliest_date,
                MAX(date) as latest_date
            FROM dim_time 
            GROUP BY year 
            ORDER BY year
        """
        time_result = hybrid_manager.execute_query(time_query)
        
        if not time_result.empty:
            # logger.info("✅ 時間維度數據檢查完成：")  # 註解掉 logging
            for _, row in time_result.iterrows():
                # logger.info(f"   {row['year']}年: {row['months']}個月, {row['total_records']}筆記錄")  # 註解掉 logging
                # logger.info(f"   日期範圍: {row['earliest_date']} 到 {row['latest_date']}")  # 註解掉 logging
                pass
        else:
            # logger.warning("⚠️  沒有找到時間維度數據")  # 註解掉 logging
            pass
        
        # 檢查銷售事實表數據
        sales_query = """
            SELECT 
                COUNT(*) as total_sales,
                SUM(amount) as total_amount,
                COUNT(DISTINCT substr(t.date, 1, 7)) as months_with_sales
            FROM sales_fact f
            JOIN dim_time t ON f.time_id = t.time_id
        """
        sales_result = hybrid_manager.execute_query(sales_query)
        
        if not sales_result.empty:
            row = sales_result.iloc[0]
            # logger.info("✅ 銷售事實表數據檢查完成：")  # 註解掉 logging
            # logger.info(f"   總銷售記錄: {row['total_sales']:,} 筆")  # 註解掉 logging
            # logger.info(f"   總銷售金額: {row['total_amount']:,.2f} 元")  # 註解掉 logging
            # logger.info(f"   有銷售的月份: {row['months_with_sales']} 個月")  # 註解掉 logging
            pass
        else:
            # logger.warning("⚠️  沒有找到銷售事實表數據")  # 註解掉 logging
            pass
        
        # 檢查產品數據
        product_query = "SELECT COUNT(*) as total_products FROM dim_product"
        product_result = hybrid_manager.execute_query(product_query)
        
        if not product_result.empty:
            # logger.info(f"✅ 產品數據: {product_result.iloc[0]['total_products']} 個產品")  # 註解掉 logging
            pass
        
        # 檢查客戶數據
        customer_query = "SELECT COUNT(*) as total_customers FROM dim_customer"
        customer_result = hybrid_manager.execute_query(customer_query)
        
        if not customer_result.empty:
            # logger.info(f"✅ 客戶數據: {customer_result.iloc[0]['total_customers']} 個客戶")  # 註解掉 logging
            pass
        
        # 檢查員工數據
        staff_query = "SELECT COUNT(*) as total_staff FROM dim_staff"
        staff_result = hybrid_manager.execute_query(staff_query)
        
        if not staff_result.empty:
            # logger.info(f"✅ 員工數據: {staff_result.iloc[0]['total_staff']} 個員工")  # 註解掉 logging
            pass
        
        # 檢查地區數據
        region_query = "SELECT COUNT(*) as total_regions FROM dim_region"
        region_result = hybrid_manager.execute_query(region_query)
        
        if not region_result.empty:
            # logger.info(f"✅ 地區數據: {region_result.iloc[0]['total_regions']} 個地區")  # 註解掉 logging
            pass
        
    except Exception as e:
        # logger.error(f"❌ 資料庫狀態檢查失敗: {e}")  # 註解掉 logging
        pass

def sync_vector_database(hybrid_manager):
    """同步向量資料庫"""
    # logger = logging.getLogger(__name__)  # 註解掉 logger
    
    # logger.info("🚀 開始同步向量資料庫...")  # 註解掉 logging
    
    try:
        # 同步產品數據
        # logger.info("📦 同步產品數據...")  # 註解掉 logging
        hybrid_manager._sync_products()
        
        # 同步客戶數據
        # logger.info("👥 同步客戶數據...")  # 註解掉 logging
        hybrid_manager._sync_customers()
        
        # 同步銷售事件數據
        # logger.info("💰 同步銷售事件數據...")  # 註解掉 logging
        hybrid_manager._sync_sales_events()
        
        # logger.info("✅ 向量資料庫同步完成！")  # 註解掉 logging
        
    except Exception as e:
        # logger.error(f"❌ 向量資料庫同步失敗: {e}")  # 註解掉 logging
        raise

def check_vector_database_status(hybrid_manager):
    """檢查向量資料庫狀態"""
    # logger = logging.getLogger(__name__)  # 註解掉 logger
    
    # logger.info("🔍 檢查向量資料庫狀態...")  # 註解掉 logging
    
    try:
        # 檢查向量資料庫狀態
        vector_status = hybrid_manager.get_vector_database_status()
        
        if vector_status.get('success'):
            # logger.info("✅ 向量資料庫狀態檢查完成：")  # 註解掉 logging
            # logger.info(f"   產品集合: {vector_status.get('collections', {}).get('products', {}).get('count', 0)} 個向量")  # 註解掉 logging
            # logger.info(f"   客戶集合: {vector_status.get('collections', {}).get('customers', {}).get('count', 0)} 個向量")  # 註解掉 logging
            # logger.info(f"   銷售事件集合: {vector_status.get('collections', {}).get('sales_events', {}).get('count', 0)} 個向量")  # 註解掉 logging
            pass
        else:
            # logger.warning("⚠️  向量資料庫狀態檢查失敗")  # 註解掉 logging
            pass
            
    except Exception as e:
        # logger.error(f"❌ 向量資料庫狀態檢查失敗: {e}")  # 註解掉 logging
        pass

def main():
    """主函數"""
    # logger = setup_logging() # 註解掉 logger
    
    # logger.info("=" * 60) # 註解掉 logging
    # logger.info("🚀 向量資料庫同步腳本開始執行") # 註解掉 logging
    # logger.info("=" * 60) # 註解掉 logging
    
    try:
        # 初始化混合資料管理器
        db_file = 'sales_cube.db'
        # logger.info(f"📁 使用資料庫檔案: {db_file}") # 註解掉 logging
        
        hybrid_manager = HybridDataManager(db_file)
        # logger.info("✅ 混合資料管理器初始化成功") # 註解掉 logging
        
        # 檢查資料庫狀態
        check_database_status(hybrid_manager)
        
        # 同步向量資料庫
        sync_vector_database(hybrid_manager)
        
        # 檢查同步後的狀態
        check_vector_database_status(hybrid_manager)
        
        # logger.info("=" * 60) # 註解掉 logging
        # logger.info("🎯 向量資料庫同步腳本執行完成！") # 註解掉 logging
        # logger.info("=" * 60) # 註解掉 logging
        
    except Exception as e:
        # logger.error(f"❌ 腳本執行失敗: {e}") # 註解掉 logging
        sys.exit(1)

if __name__ == "__main__":
    main()
