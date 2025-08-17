# app_mvc.py
# Flask 版本的 NL2Cube 智慧分析系統 - MVC 架構版本

from flask import Flask
import os
from dotenv import load_dotenv
load_dotenv()

# 導入 MVC 組件
from models.data_manager import DataManager
from controllers.analysis_controller import AnalysisController
from views.analysis_views import init_analysis_views
from routes.forecast_routes import register_forecast_routes
from routes.unified_forecast_routes import register_unified_forecast_routes

# 導入排程器
from scheduler import start_scheduler_thread, get_schedule_status

def create_app():
    """
    應用工廠函數 - 創建並配置 Flask 應用
    """
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    
    # 配置
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # 禁用靜態文件緩存
    
    # 初始化數據管理器 (Model)
    db_file = 'sales_cube.db'
    data_manager = DataManager(db_file)
    
    # 初始化分析控制器 (Controller)
    analysis_controller = AnalysisController(data_manager)
    
    # 註冊預測路由
    register_forecast_routes(app, data_manager)
    
    # 註冊統一預測路由
    register_unified_forecast_routes(app, data_manager)
    
    # 初始化視圖 (View)
    init_analysis_views(app, analysis_controller, data_manager)
    
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
    
    print("應用程式已啟動，請訪問:")
    print("  - 統一預測系統: http://127.0.0.1:5010/unified-forecast")
    print("  - 預測Agent系統: http://127.0.0.1:5010/forecast-agent-test")
    print("  - 原始預測系統: http://127.0.0.1:5010/forecast-test")
    app.run(debug=True, host='127.0.0.1', port=5010)  # 使用 localhost