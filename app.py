# app_vector.py
# Flask 版本的 NL2Cube 智慧分析系統 - 向量資料庫版本

from flask import Flask
import os
# import logging  # 註解掉 logging 模組
from dotenv import load_dotenv
load_dotenv()

# 導入 MVC 組件
from models.hybrid_data_manager import HybridDataManager
from controllers.analysis_controller import AnalysisController
from views.analysis_views import init_analysis_views
from routes.forecast_routes import register_forecast_routes
from routes.unified_forecast_routes import register_unified_forecast_routes
from routes.vector_routes import register_vector_routes

# 導入排程器
from scheduler import start_scheduler_thread, get_schedule_status

# 設定日誌 - 註解掉
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )

def create_app():
    """
    應用工廠函數 - 創建並配置 Flask 應用 (向量資料庫版本)
    """
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    
    # 配置
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # 禁用靜態文件緩存
    
    # 初始化混合資料管理器 (整合SQL和向量資料庫)
    db_file = 'sales_cube.db'
    try:
        hybrid_data_manager = HybridDataManager(db_file)
        print("✅ 混合資料管理器初始化成功")
    except Exception as e:
        print(f"❌ 混合資料管理器初始化失敗: {e}")
        raise
    
    # 初始化分析控制器 (使用混合資料管理器)
    analysis_controller = AnalysisController(hybrid_data_manager)
    
    # 註冊預測路由 (向後相容)
    register_forecast_routes(app, hybrid_data_manager)
    
    # 註冊統一預測路由 (向後相容)
    register_unified_forecast_routes(app, hybrid_data_manager)
    
    # 註冊向量搜尋路由 (新功能)
    register_vector_routes(app, hybrid_data_manager)
    
    # 初始化視圖 (向後相容)
    init_analysis_views(app, analysis_controller, hybrid_data_manager)
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    # 檢查排程狀態並決定是否啟動排程器
    schedule_status = get_schedule_status()
    
    if schedule_status['status'] == 'disabled':
        print("⏸️ 排程已停用，跳過排程器啟動")
    else:
        print("🚀 啟動定期預測排程器...")
        start_scheduler_thread()
    
    print("🎯 向量資料庫版本應用程式已啟動，請訪問:")
    print("  - 向量搜尋系統: http://127.0.0.1:5010/vector-search-test")
    print("  - 統一預測系統: http://127.0.0.1:5010/unified-forecast-test")
    print("  - 預測Agent系統: http://127.0.0.1:5010/forecast-agent-test")
    print("  - 原始預測系統: http://127.0.0.1:5010/forecast-test")
    print("\n🔍 新增向量搜尋 API:")
    print("  - POST /api/vector/search/products - 產品相似性搜尋")
    print("  - POST /api/vector/search/customers - 客戶相似性搜尋")
    print("  - POST /api/vector/search/sales - 銷售事件相似性搜尋")
    print("  - POST /api/vector/recommend/products - 產品推薦")
    print("  - POST /api/vector/detect/anomalies - 異常檢測")
    print("  - GET /api/vector/status - 向量資料庫狀態")
    print("  - POST /api/vector/refresh - 重新整理向量資料庫")
    
    app.run(debug=True, host='0.0.0.0', port=5010)  # 改為 0.0.0.0 支援外部存取

