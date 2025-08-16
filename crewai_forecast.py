# CrewAI + Gemini API 銷售預測系統 (真實數據版)
# 使用 sales_cube.db 中的真實銷售數據

import os
from dotenv import load_dotenv
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
import sqlite3
from statsmodels.tsa.statespace.sarimax import SARIMAX
import requests
import json
from crewai import Crew, Agent, Task
from langchain_core.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI
warnings.filterwarnings('ignore')

# === 1. 載入環境變數 ===
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# 檢查 API Key 是否存在
if not API_KEY or API_KEY == "your_gemini_api_key_here":
    print("❌ 錯誤：請設置 GOOGLE_API_KEY 環境變數")
    print("請在 .env 檔案中添加：GOOGLE_API_KEY=你的Gemini API Key")
    exit(1)

# === 2. 配置 Gemini LLM ===
def create_gemini_llm():
    """創建 Gemini LLM 實例"""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            google_api_key=API_KEY,
            temperature=0.7,
            max_tokens=2048
        )
        return llm
    except ImportError:
        print("❌ 錯誤：需要安裝 langchain-google-genai")
        print("請執行：pip install langchain-google-genai")
        exit(1)
    except Exception as e:
        print(f"❌ Gemini LLM 創建失敗：{e}")
        exit(1)

# === 3. 資料庫分析工具 ===
class DatabaseAnalysisTools:
    """資料庫分析工具類"""
    
    def __init__(self, db_path='sales_cube.db'):
        self.db_path = db_path
    
    def get_database_info(self):
        """獲取資料庫基本信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 獲取表信息
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            # 獲取各表的記錄數
            table_counts = {}
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                table_counts[table_name] = count
            
            conn.close()
            
            return {
                'success': True,
                'tables': [table[0] for table in tables],
                'table_counts': table_counts,
                'database_path': self.db_path
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_sales_summary(self):
        """獲取銷售數據摘要"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 月度銷售摘要
            monthly_query = """
            SELECT 
                substr(dt.date, 1, 7) as month,
                SUM(sf.amount) as total_sales,
                COUNT(sf.sale_id) as transaction_count,
                AVG(sf.amount) as avg_sale_amount
            FROM sales_fact sf
            JOIN dim_time dt ON sf.time_id = dt.time_id
            GROUP BY substr(dt.date, 1, 7)
            ORDER BY month
            """
            monthly_df = pd.read_sql_query(monthly_query, conn)
            
            # 產品類別摘要
            product_query = """
            SELECT 
                dp.category,
                SUM(sf.amount) as category_sales,
                COUNT(sf.sale_id) as category_transactions
            FROM sales_fact sf
            JOIN dim_product dp ON sf.product_id = dp.product_id
            GROUP BY dp.category
            ORDER BY category_sales DESC
            """
            product_df = pd.read_sql_query(product_query, conn)
            
            # 地區摘要
            region_query = """
            SELECT 
                dr.region_name,
                SUM(sf.amount) as region_sales,
                COUNT(sf.sale_id) as region_transactions
            FROM sales_fact sf
            JOIN dim_region dr ON sf.region_id = dr.region_id
            GROUP BY dr.region_name
            ORDER BY region_sales DESC
            """
            region_df = pd.read_sql_query(region_query, conn)
            
            # 時間範圍
            time_query = """
            SELECT MIN(date), MAX(date) FROM dim_time
            """
            time_range = pd.read_sql_query(time_query, conn)
            
            conn.close()
            
            return {
                'success': True,
                'monthly_data': monthly_df.to_dict('records'),
                'product_data': product_df.to_dict('records'),
                'region_data': region_df.to_dict('records'),
                'time_range': {
                    'start_date': time_range.iloc[0, 0],
                    'end_date': time_range.iloc[0, 1]
                },
                'total_records': len(monthly_df),
                'total_sales': monthly_df['total_sales'].sum(),
                'total_transactions': monthly_df['transaction_count'].sum()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_data_quality_report(self):
        """獲取數據品質報告"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 檢查缺失值
            missing_check = """
            SELECT 
                'sales_fact' as table_name,
                COUNT(*) as total_rows,
                SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END) as null_amount,
                SUM(CASE WHEN sale_id IS NULL THEN 1 ELSE 0 END) as null_sale_id
            FROM sales_fact
            """
            missing_df = pd.read_sql_query(missing_check, conn)
            
            # 檢查異常值
            outlier_check = """
            SELECT 
                MIN(amount) as min_amount,
                MAX(amount) as max_amount,
                AVG(amount) as avg_amount,
                STDDEV(amount) as std_amount
            FROM sales_fact
            """
            outlier_df = pd.read_sql_query(outlier_check, conn)
            
            # 檢查時間序列連續性
            time_continuity = """
            SELECT 
                COUNT(DISTINCT date) as unique_dates,
                MIN(date) as min_date,
                MAX(date) as max_date
            FROM dim_time
            """
            continuity_df = pd.read_sql_query(time_continuity, conn)
            
            conn.close()
            
            return {
                'success': True,
                'missing_data': missing_df.to_dict('records'),
                'outlier_stats': outlier_df.to_dict('records'),
                'time_continuity': continuity_df.to_dict('records')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# === 4. 創建工具實例 ===
db_tools = DatabaseAnalysisTools()

# === 5. 真實數據預測工具 ===
class RealDataForecastTools:
    """使用真實數據的預測工具"""
    
    def __init__(self, db_path='sales_cube.db'):
        self.db_path = db_path
        
    def get_sales_data(self):
        """獲取真實銷售數據"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 獲取月度銷售數據
            query = """
            SELECT 
                substr(dt.date, 1, 7) as month,
                SUM(sf.amount) as total_sales,
                COUNT(sf.sale_id) as transaction_count,
                AVG(sf.amount) as avg_sale_amount
            FROM sales_fact sf
            JOIN dim_time dt ON sf.time_id = dt.time_id
            GROUP BY substr(dt.date, 1, 7)
            ORDER BY month
            """
            df = pd.read_sql_query(query, conn)
            
            # 獲取產品類別銷售數據
            product_query = """
            SELECT 
                dp.category,
                SUM(sf.amount) as category_sales,
                COUNT(sf.sale_id) as category_transactions
            FROM sales_fact sf
            JOIN dim_product dp ON sf.product_id = dp.product_id
            GROUP BY dp.category
            ORDER BY category_sales DESC
            """
            product_df = pd.read_sql_query(product_query, conn)
            
            # 獲取地區銷售數據
            region_query = """
            SELECT 
                dr.region_name,
                SUM(sf.amount) as region_sales,
                COUNT(sf.sale_id) as region_transactions
            FROM sales_fact sf
            JOIN dim_region dr ON sf.region_id = dr.region_id
            GROUP BY dr.region_name
            ORDER BY region_sales DESC
            """
            region_df = pd.read_sql_query(region_query, conn)
            
            conn.close()
            
            if df.empty:
                print("⚠️  資料庫中沒有銷售數據，使用模擬數據")
                return self.generate_sample_data()
            
            print(f"✅ 成功從資料庫獲取 {len(df)} 個月的真實銷售數據")
            print(f"📊 數據範圍：{df['month'].min()} 到 {df['month'].max()}")
            print(f"💰 總銷售額：{df['total_sales'].sum():,.2f} 元")
            print(f"🛒 總交易數：{df['transaction_count'].sum():,} 筆")
            
            return {
                'monthly_data': df,
                'product_data': product_df,
                'region_data': region_df,
                'dates': df['month'].tolist(),
                'sales': df['total_sales'].tolist()
            }
            
        except Exception as e:
            print(f"❌ 無法連接資料庫：{e}")
            print("使用模擬數據作為備用")
            return self.generate_sample_data()
    
    def generate_sample_data(self):
        """生成示例銷售數據（備用）"""
        dates = []
        sales_data = []
        
        # 使用固定日期作為基準，確保時間軸一致性
        base_date = datetime(2025, 7, 10)  # 與其他模組保持一致
        for i in range(24):
            date = base_date - timedelta(days=30*(23-i))
            dates.append(date.strftime("%Y-%m"))
            
            base_sales = 100000
            trend = i * 5000
            seasonal = 20000 * np.sin(2 * np.pi * i / 12)
            noise = np.random.normal(0, 10000)
            
            sales = base_sales + trend + seasonal + noise
            sales_data.append(max(0, sales))
        
        return {
            'dates': dates,
            'sales': sales_data,
            'monthly_data': pd.DataFrame({'month': dates, 'total_sales': sales_data})
        }
    
    def forecast_sales(self, periods=12):
        """執行銷售預測"""
        try:
            data = self.get_sales_data()
            dates = data['dates']
            sales_data = data['sales']
            
            if len(dates) < 3:
                print("❌ 數據點不足，無法進行預測")
                return {
                    'success': False,
                    'error': '數據點不足，至少需要3個數據點'
                }
            
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
            base_date = datetime(2025, 7, 10)  # 與其他模組保持一致
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
            
            # 計算統計信息
            total_forecast = sum(item['forecast_sales'] for item in forecast_data)
            avg_forecast = total_forecast / len(forecast_data)
            
            # 計算歷史統計信息
            historical_stats = {
                'total_sales': sum(sales_data),
                'avg_monthly_sales': np.mean(sales_data),
                'sales_std': np.std(sales_data),
                'min_sales': min(sales_data),
                'max_sales': max(sales_data),
                'data_points': len(sales_data)
            }
            
            return {
                'success': True,
                'forecast_data': forecast_data,
                'periods': periods,
                'total_forecast': total_forecast,
                'avg_forecast': avg_forecast,
                'historical_data': {
                    'dates': dates,
                    'sales': sales_data,
                    'stats': historical_stats
                },
                'raw_data': data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# === 6. 創建工具實例 ===
forecast_tools = RealDataForecastTools()

# === 7. 創建 Gemini LLM ===
gemini_llm = create_gemini_llm()

# === 8. 定義工具函數 ===
def analyze_database_tool(tool_input):
    """分析資料庫工具"""
    db_info = db_tools.get_database_info()
    sales_summary = db_tools.get_sales_summary()
    quality_report = db_tools.get_data_quality_report()
    
    return {
        'database_info': db_info,
        'sales_summary': sales_summary,
        'quality_report': quality_report
    }

def get_forecast_data_tool(tool_input):
    """獲取預測數據工具"""
    # 從 tool_input 中提取 periods 參數，如果沒有則使用預設值
    periods = 12
    if isinstance(tool_input, dict) and 'periods' in tool_input:
        periods = tool_input['periods']
    elif isinstance(tool_input, str):
        try:
            # 嘗試從字符串中提取數字
            import re
            numbers = re.findall(r'\d+', tool_input)
            if numbers:
                periods = int(numbers[0])
        except:
            pass
    
    return forecast_tools.forecast_sales(periods)

# === 9. 創建工具 ===
database_tool = Tool(
    name="analyze_database",
    description="分析 sales_cube.db 資料庫中的真實銷售數據，包括數據摘要、品質報告和統計信息",
    func=analyze_database_tool
)

forecast_tool = Tool(
    name="get_forecast_data",
    description="使用真實銷售數據執行 SARIMAX 預測分析",
    func=get_forecast_data_tool
)

# === 10. 定義 Agents ===
data_agent = Agent(
    role="資料工程師",
    goal="分析真實銷售數據並提供數據品質報告",
    backstory="專業的資料工程師，擅長資料清理和預處理。我會分析真實銷售數據的品質並提供詳細的數據摘要。",
    llm=gemini_llm,
    tools=[database_tool],
    verbose=True
)

forecast_agent = Agent(
    role="預測分析師",
    goal="使用真實數據執行銷售預測並分析結果",
    backstory="資深預測分析師，精通時間序列分析。我會使用真實銷售數據構建 SARIMAX 模型並提供統計分析。",
    llm=gemini_llm,
    tools=[forecast_tool],
    verbose=True
)

analysis_agent = Agent(
    role="業務分析師",
    goal="基於真實數據分析預測結果並提供業務洞察",
    backstory="資深業務分析師，擅長市場分析和策略規劃。我會基於真實銷售數據提供趨勢分析、風險評估和策略建議。",
    llm=gemini_llm,
    verbose=True
)

# === 11. 定義 Tasks ===
data_task = Task(
    description="""
    作為資料工程師，請執行以下任務：
    
    1. 使用 analyze_database 工具分析 sales_cube.db 中的真實銷售數據
    2. 檢查數據品質，包括：
       - 數據完整性（缺失值、重複值）
       - 異常值檢測
       - 數據格式檢查
       - 時間序列的連續性
    3. 提供數據摘要，包括：
       - 數據點數量和時間範圍
       - 銷售額統計（總額、平均值、標準差、最大值、最小值）
       - 交易數量統計
       - 產品類別分析
       - 地區銷售分析
    4. 識別數據中的模式和趨勢
    
    請提供詳細的真實數據分析報告。
    """,
    expected_output="完整的真實銷售數據分析報告和品質評估",
    agent=data_agent
)

forecast_task = Task(
    description="""
    作為預測分析師，請執行以下任務：
    
    1. 接收資料工程師提供的真實銷售數據分析
    2. 使用 get_forecast_data 工具進行銷售預測，包括：
       - 模型參數選擇 (p, d, q) 和季節性參數 (P, D, Q, s)
       - 模型擬合和診斷
       - 預測準確性評估
    3. 分析預測結果，包括：
       - 預測值統計摘要
       - 置信區間分析
       - 趨勢分析
       - 季節性模式識別
    4. 提供詳細的預測報告
    
    請提供完整的預測結果和統計分析。
    """,
    expected_output="詳細的預測結果和統計分析報告",
    agent=forecast_agent,
    context=[data_task]
)

analysis_task = Task(
    description="""
    作為業務分析師，請執行以下任務：
    
    1. 接收預測分析師的預測結果
    2. 基於真實數據進行業務分析，包括：
       - 銷售趨勢分析（基於真實歷史數據）
       - 市場機會評估
       - 風險因素識別
       - 競爭環境分析
    3. 提供策略建議，包括：
       - 資源配置建議（基於真實銷售表現）
       - 營銷策略建議
       - 風險管理建議
       - 績效監控建議
    
    請提供完整的業務分析報告和策略建議。
    """,
    expected_output="完整的業務分析報告和策略建議",
    agent=analysis_agent,
    context=[forecast_task]
)

# === 12. 組裝 Crew ===
crew = Crew(
    agents=[data_agent, forecast_agent, analysis_agent],
    tasks=[data_task, forecast_task, analysis_task],
    verbose=True
)

# === 13. 執行函數 ===
def execute_crewai_forecast(periods=12):
    """執行 CrewAI 預測流程"""
    try:
        print("🚀 開始執行 CrewAI + Gemini 真實數據預測流程...")
        print(f"📊 預測期數：{periods}")
        print(f"🔑 使用 Gemini API Key: {API_KEY[:10]}...")
        
        # 先執行預測獲取數據
        print("📋 從 sales_cube.db 獲取真實銷售數據...")
        forecast_result = forecast_tools.forecast_sales(periods)
        
        if not forecast_result['success']:
            print(f"❌ 預測失敗：{forecast_result['error']}")
            return {
                'success': False,
                'error': forecast_result['error'],
                'timestamp': datetime.now().isoformat()
            }
        
        print("✅ 真實數據預測完成")
        print(f"📊 預測數據：{len(forecast_result['forecast_data'])} 個期間")
        print(f"💰 總預測額：{forecast_result['total_forecast']:,.0f} 元")
        print(f"📈 平均月預測：{forecast_result['avg_forecast']:,.0f} 元")
        
        # 顯示歷史數據統計
        hist_stats = forecast_result['historical_data']['stats']
        print(f"📊 歷史數據統計：")
        print(f"   - 數據點數：{hist_stats['data_points']} 個月")
        print(f"   - 總銷售額：{hist_stats['total_sales']:,.0f} 元")
        print(f"   - 平均月銷售：{hist_stats['avg_monthly_sales']:,.0f} 元")
        print(f"   - 銷售標準差：{hist_stats['sales_std']:,.0f} 元")
        
        # 執行 CrewAI 流程
        print("🤖 開始 CrewAI 分析流程...")
        result = crew.kickoff()
        
        print("✅ CrewAI 預測流程完成")
        return {
            'success': True,
            'crewai_result': result,
            'forecast_data': forecast_result,
            'periods': periods,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ CrewAI 預測流程失敗：{str(e)}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# === 14. 主程式執行 ===
if __name__ == "__main__":
    print("🚀 開始執行 CrewAI + Gemini 真實數據銷售預測系統...")
    print(f"✅ 使用 Gemini API Key: {API_KEY[:10]}...")
    print("📊 使用 sales_cube.db 中的真實銷售數據")
    
    try:
        # 執行 CrewAI 預測
        result = execute_crewai_forecast(periods=12)
        
        print("=" * 60)
        print("CrewAI + Gemini 真實數據預測結果：")
        print("=" * 60)
        
        if result['success']:
            print("✅ 預測成功完成")
            print(f"📅 預測期數：{result['periods']}")
            print(f"⏰ 執行時間：{result['timestamp']}")
            
            # 顯示預測數據摘要
            forecast_data = result['forecast_data']
            print(f"📊 預測數據點數：{len(forecast_data['forecast_data'])}")
            print(f"💰 總預測銷售額：{forecast_data['total_forecast']:,.0f} 元")
            print(f"📈 平均月銷售額：{forecast_data['avg_forecast']:,.0f} 元")
            
            # 顯示歷史數據摘要
            hist_data = forecast_data['historical_data']
            print(f"📊 歷史數據摘要：")
            print(f"   - 數據範圍：{hist_data['dates'][0]} 到 {hist_data['dates'][-1]}")
            print(f"   - 數據點數：{hist_data['stats']['data_points']} 個月")
            print(f"   - 總歷史銷售：{hist_data['stats']['total_sales']:,.0f} 元")
            
            print("\n📋 CrewAI 分析報告：")
            print("-" * 40)
            print(result['crewai_result'])
        else:
            print(f"❌ 預測失敗：{result['error']}")
        
        print("=" * 60)
        print("✅ CrewAI + Gemini 真實數據銷售預測系統執行完成！")
        
    except Exception as e:
        print(f"❌ 系統執行失敗：{e}")
        print("請檢查 API Key 是否正確，以及網路連線是否正常")

# === 15. 安裝說明 ===
"""
如果遇到版本兼容性問題，請執行以下命令安裝兼容版本：

pip uninstall crewai langchain langchain-core langchain-community
pip install crewai==0.11.0
pip install langchain==0.0.350
pip install langchain-core==0.0.12
pip install langchain-community==0.0.10
pip install langchain-google-genai==0.0.6
pip install python-dotenv
pip install pandas numpy statsmodels

然後確保 .env 檔案中有正確的 GOOGLE_API_KEY
""" 