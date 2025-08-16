# CrewAI 預測路由
# 整合到現有 Flask 應用程式

from flask import jsonify, request
import os
import sys
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 導入 CrewAI 相關模組
try:
    from crewai import Crew, Agent, Task
    from langchain_core.tools import Tool
    import requests
    import numpy as np
    import pandas as pd
    from datetime import datetime, timedelta
    import sqlite3
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from dotenv import load_dotenv
    
    # 載入環境變數
    load_dotenv()
    API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # 定義 Gemini Web API 呼叫函數
    GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}"
    
    def gemini_prompt(prompt_text):
        """用 Gemini API 回應問題"""
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}]
        }
        response = requests.post(GEMINI_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
    
    # 預測工具類別
    class CrewAIForecastTools:
        """CrewAI 預測工具"""
        
        def __init__(self, db_path='sales_cube.db'):
            self.db_path = db_path
            
        def get_sales_data(self):
            """獲取銷售數據"""
            try:
                conn = sqlite3.connect(self.db_path)
                current_date = datetime.now()
                current_month = current_date.strftime('%Y-%m')
                
                query = """
                SELECT 
                    substr(dt.date, 1, 7) as month,
                    SUM(sf.amount) as total_sales
                FROM sales_fact sf
                JOIN dim_time dt ON sf.time_id = dt.time_id
                WHERE substr(dt.date, 1, 7) <= ?
                GROUP BY substr(dt.date, 1, 7)
                ORDER BY month
                """
                df = pd.read_sql_query(query, conn, params=[current_month])
                conn.close()
                
                if df.empty:
                    return self.generate_sample_data()
                
                return df['month'].tolist(), df['total_sales'].tolist()
                
            except Exception as e:
                print(f"⚠️  無法連接資料庫：{e}，使用模擬數據")
                return self.generate_sample_data()
        
        def generate_sample_data(self):
            """生成示例銷售數據"""
            dates = []
            sales_data = []
            
            current_date = datetime.now()
            for i in range(24):
                date = current_date - timedelta(days=30*(23-i))
                dates.append(date.strftime("%Y-%m"))
                
                base_sales = 100000
                trend = i * 5000
                seasonal = 20000 * np.sin(2 * np.pi * i / 12)
                noise = np.random.normal(0, 10000)
                
                sales = base_sales + trend + seasonal + noise
                sales_data.append(max(0, sales))
            
            return dates, sales_data
        
        def forecast_sales(self, periods=12):
            """執行銷售預測"""
            try:
                dates, sales_data = self.get_sales_data()
                historical_series = pd.Series(sales_data, index=pd.to_datetime(dates))
                
                # 使用 SARIMAX 模型
                model = SARIMAX(historical_series,
                              order=(1, 1, 1),
                              seasonal_order=(1, 1, 1, 12),
                              enforce_stationarity=False,
                              enforce_invertibility=False)
                
                results = model.fit(disp=False)
                forecast = results.forecast(steps=periods)
                
                # 生成預測日期 - 使用固定基準日期確保一致性
                forecast_dates = []
                
                # 從2025年8月開始預測
                start_year = 2025
                start_month = 8
                
                for i in range(periods):
                    if start_month > 12:
                        start_month = 1
                        start_year += 1
                    forecast_dates.append(f"{start_year}-{start_month:02d}")
                    start_month += 1
                
                # 處理預測結果
                forecast_data = []
                for i, (date, value) in enumerate(zip(forecast_dates, forecast.values)):
                    forecast_data.append({
                        'period': date,
                        'forecast_sales': round(float(value), 2),
                        'period_number': i + 1
                    })
                
                return {
                    'success': True,
                    'forecast_data': forecast_data,
                    'periods': periods,
                    'total_forecast': sum(item['forecast_sales'] for item in forecast_data),
                    'avg_forecast': sum(item['forecast_sales'] for item in forecast_data) / len(forecast_data),
                    'historical_data': {
                        'dates': dates,
                        'sales': sales_data,
                        'data_points': len(sales_data)
                    }
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }
    
    # 創建工具實例
    forecast_tools = CrewAIForecastTools()
    
    # 工具函數
    def data_collection_tool():
        """資料收集工具"""
        dates, sales_data = forecast_tools.get_sales_data()
        return f"歷史數據點數: {len(dates)}, 數據範圍: {dates[0]} 到 {dates[-1]}, 平均銷售額: {np.mean(sales_data):.2f}"
    
    def forecast_execution_tool(periods=12):
        """預測執行工具"""
        result = forecast_tools.forecast_sales(periods)
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    def business_analysis_tool(forecast_result_json):
        """業務分析工具"""
        try:
            forecast_result = json.loads(forecast_result_json)
            
            if not forecast_result.get('success', False):
                return "預測失敗，無法進行業務分析"
            
            forecast_data = forecast_result.get('forecast_data', [])
            total_forecast = forecast_result.get('total_forecast', 0)
            avg_forecast = forecast_result.get('avg_forecast', 0)
            
            # 分析趨勢
            sales_values = [item['forecast_sales'] for item in forecast_data]
            first_quarter_avg = sum(sales_values[:3]) / 3 if len(sales_values) >= 3 else avg_forecast
            last_quarter_avg = sum(sales_values[-3:]) / 3 if len(sales_values) >= 3 else avg_forecast
            trend_direction = "上升" if last_quarter_avg > first_quarter_avg else "下降"
            
            prompt = f"""
            作為業務分析師，請分析以下銷售預測結果：

            預測數據：
            - 總預測銷售額：{total_forecast:,.0f} 元
            - 平均月銷售額：{avg_forecast:,.0f} 元
            - 預測期數：{len(forecast_data)} 個月
            - 整體趨勢：{trend_direction}

            詳細預測：
            {chr(10).join([f"  • {item['period']}: {item['forecast_sales']:,.0f} 元" for item in forecast_data])}

            請提供：
            1. 業務趨勢分析
            2. 關鍵風險因素
            3. 改善建議
            4. 策略重點
            """
            
            return gemini_prompt(prompt)
            
        except Exception as e:
            return f"業務分析失敗：{str(e)}"
    
    # 將工具包裝成 LangChain Tools
    data_collection_tool = Tool.from_function(
        name="DataCollection",
        description="收集歷史銷售數據",
        func=data_collection_tool
    )
    
    forecast_execution_tool = Tool.from_function(
        name="ForecastExecution",
        description="執行銷售預測",
        func=forecast_execution_tool
    )
    
    business_analysis_tool = Tool.from_function(
        name="BusinessAnalysis",
        description="進行業務分析",
        func=business_analysis_tool
    )
    
    gemini_tool = Tool.from_function(
        name="GeminiAPI",
        description="用 Gemini API 回應問題",
        func=gemini_prompt
    )
    
    # 定義 Agents
    data_agent = Agent(
        role="資料工程師",
        goal="收集與預處理銷售歷史數據",
        backstory="專業的資料工程師，擅長資料清理和預處理",
        tools=[data_collection_tool, gemini_tool]
    )
    
    forecast_agent = Agent(
        role="預測分析師",
        goal="執行銷售預測模型",
        backstory="資深預測分析師，精通時間序列分析",
        tools=[forecast_execution_tool, gemini_tool]
    )
    
    analysis_agent = Agent(
        role="業務分析師",
        goal="分析預測結果並提供業務洞察",
        backstory="資深業務分析師，擅長市場分析和策略規劃",
        tools=[business_analysis_tool, gemini_tool]
    )
    
    # 定義 Tasks
    data_task = Task(
        description="收集歷史銷售數據並檢查數據品質",
        expected_output="歷史銷售數據摘要",
        agent=data_agent
    )
    
    forecast_task = Task(
        description="使用 SARIMAX 模型執行銷售預測",
        expected_output="詳細的預測結果",
        agent=forecast_agent,
        context=[data_task]
    )
    
    analysis_task = Task(
        description="分析預測結果並提供業務建議",
        expected_output="業務分析報告",
        agent=analysis_agent,
        context=[forecast_task]
    )
    
    # 組裝 Crew
    crew = Crew(
        agents=[data_agent, forecast_agent, analysis_agent],
        tasks=[data_task, forecast_task, analysis_task],
        verbose=True
    )
    
    CREWAI_AVAILABLE = True
    
except ImportError as e:
    print(f"⚠️  CrewAI 相關套件未安裝：{e}")
    CREWAI_AVAILABLE = False
except Exception as e:
    print(f"⚠️  CrewAI 初始化失敗：{e}")
    CREWAI_AVAILABLE = False

def register_crewai_forecast_routes(app):
    """註冊 CrewAI 預測路由"""
    
    @app.route('/crewai/forecast', methods=['POST'])
    def crewai_forecast_endpoint():
        """CrewAI 預測端點"""
        if not CREWAI_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'CrewAI 功能未啟用，請安裝相關套件'
            }), 400
        
        try:
            data = request.json
            periods = data.get('periods', 12)
            
            print(f"🚀 開始執行 CrewAI 預測，期數：{periods}")
            
            # 執行 CrewAI 流程
            result = crew.kickoff()
            
            print("✅ CrewAI 預測完成")
            
            return jsonify({
                'success': True,
                'crewai_result': result,
                'periods': periods,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            print(f"❌ CrewAI 預測失敗：{str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    @app.route('/crewai/status', methods=['GET'])
    def crewai_status_endpoint():
        """CrewAI 狀態檢查端點"""
        return jsonify({
            'available': CREWAI_AVAILABLE,
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/crewai/test', methods=['GET'])
    def crewai_test_endpoint():
        """CrewAI 測試端點"""
        if not CREWAI_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'CrewAI 功能未啟用'
            }), 400
        
        try:
            # 簡單測試
            test_result = data_collection_tool()
            
            return jsonify({
                'success': True,
                'test_result': test_result,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500 