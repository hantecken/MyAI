# 統一預測系統 - 結合業績預測和分析結果預測的優點
# 整合 matplotlib 細膩圖表 + CrewAI 深度分析

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
import matplotlib
matplotlib.use('Agg')  # 設置 matplotlib 使用 Agg 後端
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
import warnings
from matplotlib.font_manager import FontProperties
from pandas.tseries.offsets import DateOffset
import requests
import json
from dotenv import load_dotenv
import math
# import logging  # 註解掉 logging 模組
import hashlib
import pickle
warnings.filterwarnings('ignore')

# 設置日誌記錄 - 註解掉
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('unified_forecaster.log'),
#         logging.StreamHandler()
#     ]
# )

# 載入環境變數
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# 設定中文字型
font_paths = [
    '/System/Library/Fonts/PingFang.ttc',
    '/System/Library/Fonts/STHeiti Light.ttc',
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
    '/System/Library/Fonts/Arial Unicode MS.ttf',
    '/System/Library/Fonts/Helvetica.ttc'
]

chinese_font = None
try:
    for font_path in font_paths:
        if os.path.exists(font_path):
            chinese_font = FontProperties(fname=font_path)
            # logging.info(f"成功載入字型: {font_path}")  # 註解掉 logging
            break
    
    if chinese_font is None:
        import matplotlib.font_manager as fm
        chinese_fonts = [f.name for f in fm.fontManager.ttflist if 'chinese' in f.name.lower() or 'cjk' in f.name.lower()]
        if chinese_fonts:
            chinese_font = FontProperties(family=chinese_fonts[0])
            # logging.info(f"使用內建中文字型: {chinese_fonts[0]}")  # 註解掉 logging
        else:
            chinese_font = FontProperties()
            # logging.info("使用預設字型")  # 註解掉 logging
except Exception as e:
    # logging.error(f"字型設定錯誤: {e}")  # 註解掉 logging
    chinese_font = FontProperties()

def safe_float(value):
    """安全轉換為浮點數，處理NaN和無效值"""
    try:
        if pd.isna(value) or value is None:
            return 0.0
        float_val = float(value)
        if math.isnan(float_val) or math.isinf(float_val):
            return 0.0
        return float_val
    except (ValueError, TypeError):
        return 0.0

class UnifiedForecaster:
    """
    統一預測器類 - 結合業績預測和分析結果預測的優點
    確保數據一致性和完整的AI分析功能
    """
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.default_periods = 12
        self.default_seasonal_periods = 12
        self.api_key = API_KEY
        
        # 快取機制
        self.cache_dir = 'cache'
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # 統一的預測模型參數，確保一致性
        # 基於歷史數據分析優化的參數，能更好地捕捉季節性模式
        self.model_params = {
            'order': (1, 1, 2),  # 增加MA項複雜度，更好地捕捉短期波動
            'seasonal_order': (1, 1, 1, 12),  # 保持季節性建模
            'enforce_stationarity': False,
            'enforce_invertibility': False
        }
        
        # logging.info("統一預測器初始化完成")  # 註解掉 logging
        
    def _get_cache_key(self, forecast_type, periods, enable_ai_analysis):
        """生成快取鍵值"""
        cache_data = {
            'forecast_type': forecast_type,
            'periods': periods,
            'enable_ai_analysis': enable_ai_analysis,
            'timestamp': datetime.now().strftime('%Y%m%d')  # 每天更新快取
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _load_from_cache(self, cache_key):
        """從快取載入結果"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    cached_result = pickle.load(f)
                # logging.info(f"從快取載入結果: {cache_key}")  # 註解掉 logging
                return cached_result
            except Exception as e:
                # logging.warning(f"快取載入失敗: {e}")  # 註解掉 logging
                pass # 註解掉 logging
        return None
    
    def _save_to_cache(self, cache_key, result):
        """儲存結果到快取"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
            # logging.info(f"結果已儲存到快取: {cache_key}")  # 註解掉 logging
        except Exception as e:
            # logging.warning(f"快取儲存失敗: {e}")  # 註解掉 logging
            pass # 註解掉 logging
    
    def generate_unified_forecast(self, forecast_type='month', periods=12, enable_ai_analysis=True):
        """
        生成統一預測結果
        Args:
            forecast_type: 預測類型 ('month', 'quarter', 'year')
            periods: 預測期數
            enable_ai_analysis: 是否啟用 AI 分析
        Returns:
            dict: 包含預測結果、圖表和 AI 分析的完整字典
        """
        try:
            # 檢查快取
            cache_key = self._get_cache_key(forecast_type, periods, enable_ai_analysis)
            cached_result = self._load_from_cache(cache_key)
            if cached_result:
                return cached_result
            
            # logging.info("🚀 開始統一預測流程...")  # 註解掉 logging
            
            # 1. 執行基礎預測
            # logging.info("📊 執行基礎預測...")  # 註解掉 logging
            forecast_result = self._execute_basic_forecast(forecast_type, periods)
            
            if not forecast_result['success']:
                return forecast_result
            
            # 2. 生成細膩圖表
            # logging.info("📈 生成細膩圖表...")  # 註解掉 logging
            chart_result = self._generate_detailed_chart(forecast_result)
            forecast_result.update(chart_result)
            
            # 3. 執行 AI 分析（如果啟用）
            if enable_ai_analysis and self.api_key:
                # logging.info("🤖 執行 AI 分析...")  # 註解掉 logging
                ai_analysis = self._generate_comprehensive_ai_analysis(forecast_result)
                forecast_result['ai_analysis'] = ai_analysis
            else:
                forecast_result['ai_analysis'] = {
                    'success': False,
                    'message': 'AI 分析未啟用或 API Key 未設定'
                }
            
            # 儲存到快取
            self._save_to_cache(cache_key, forecast_result)
            
            # logging.info("✅ 統一預測完成")  # 註解掉 logging
            return forecast_result
            
        except Exception as e:
            # logging.error(f"❌ 統一預測失敗: {str(e)}")  # 註解掉 logging
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _execute_basic_forecast(self, forecast_type, periods):
        """執行基礎預測，使用統一的模型參數確保一致性"""
        try:
            # 從資料庫獲取歷史數據
            historical_data, date_labels = self._get_historical_data()
            
            # 資料預處理
            historical_data = pd.Series(historical_data)
            historical_data = historical_data.astype(float)
            historical_data_for_plot = historical_data.values
            
            # 自動選擇最佳參數（如果數據量足夠）
            if len(historical_data) >= 24:  # 至少需要24個數據點
                selected_params = self._auto_select_best_parameters(historical_data)
            else:
                selected_params = self.model_params
                # logging.warning("📊 數據量不足，使用預設參數")  # 註解掉 logging
            
            # 使用選定的SARIMAX模型參數進行預測
            model = SARIMAX(historical_data,
                          order=selected_params['order'],
                          seasonal_order=selected_params['seasonal_order'],
                          enforce_stationarity=selected_params['enforce_stationarity'],
                          enforce_invertibility=selected_params['enforce_invertibility'])
            
            results = model.fit(disp=False)
            
            # 根據預測類型調整預測期數
            if forecast_type == 'quarter':
                months_to_forecast = periods * 3
            elif forecast_type == 'year':
                months_to_forecast = periods * 12
            else:
                months_to_forecast = periods
                
            # 生成預測
            forecast = results.forecast(steps=months_to_forecast)
            
            # 從系統當前日期的下個月開始預測
            current_date = datetime.now()
            start_date = current_date.replace(day=1)
            if current_date.month == 12:
                start_date = start_date.replace(year=current_date.year + 1, month=1)
            else:
                start_date = start_date.replace(month=current_date.month + 1)
            
            # 生成預測期間的日期標籤
            forecast_dates = []
            for i in range(months_to_forecast):
                next_date = start_date + pd.DateOffset(months=i)
                forecast_dates.append(f"{next_date.year}/{next_date.month:02d}")
            
            # 轉換預測結果
            forecast_data = self._process_forecast_results(forecast, forecast_type, periods, forecast_dates)
            
            # 計算總預測銷售額和平均預測銷售額
            total_forecast = sum(item['forecast_sales'] for item in forecast_data)
            avg_forecast = total_forecast / len(forecast_data) if len(forecast_data) > 0 else 0
            
            # 計算預測時間範圍
            forecast_range = f"{forecast_dates[0]} - {forecast_dates[-1]}"
            
            # 生成 period_text 以保持與原始系統的兼容性
            period_text_map = {
                'month': '月',
                'quarter': '季', 
                'year': '年'
            }
            period_text = period_text_map.get(forecast_type, '月')
            
            # 準備歷史統計數據
            historical_stats = {
                'data_points': len(historical_data_for_plot),
                'total_sales': safe_float(sum(historical_data_for_plot)),
                'avg_monthly_sales': safe_float(np.mean(historical_data_for_plot)),
                'sales_std': safe_float(np.std(historical_data_for_plot))
            }
            
            # 生成 forecast_summary 以保持與前端代碼的兼容性
            forecast_summary = self._generate_forecast_summary(
                forecast_type, periods, total_forecast, avg_forecast, 
                forecast_data, historical_stats
            )
            
            # 安全處理模型摘要統計
            model_summary = {
                'aic': safe_float(results.aic),
                'bic': safe_float(results.bic),
                'hqic': safe_float(results.hqic)
            }
            
            return {
                'success': True,
                'forecast_data': forecast_data,
                'historical_data': {
                    'data': [safe_float(x) for x in historical_data_for_plot.tolist()],
                    'dates': date_labels,
                    'stats': historical_stats
                },
                'total_forecast': safe_float(total_forecast),
                'avg_forecast': safe_float(avg_forecast),
                'forecast_range': forecast_range,
                'periods': periods,
                'forecast_type': forecast_type,
                'period_text': period_text,  # 添加 period_text 字段
                'forecast_summary': forecast_summary,  # 添加 forecast_summary 字段
                'model_info': {
                    'training_period': {
                        'start': date_labels[0] if date_labels else '',
                        'end': date_labels[-1] if date_labels else ''
                    },
                    'model_type': 'SARIMAX',
                    'parameters': selected_params,  # 使用實際選擇的參數
                    'model_summary': model_summary,
                    'parameter_selection': 'auto' if len(historical_data) >= 24 else 'default'
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            # logging.error(f"基礎預測失敗: {str(e)}")  # 註解掉 logging
            return {
                'success': False,
                'error': f"基礎預測失敗: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _auto_select_best_parameters(self, historical_data):
        """
        自動選擇最佳的SARIMAX參數
        基於AIC和BIC評分選擇最佳模型
        """
        try:
            best_aic = float('inf')
            best_params = None
            
            # 參數範圍（基於數據特性優化）
            p_values = [0, 1, 2]
            d_values = [1]  # 通常1次差分即可
            q_values = [0, 1, 2]
            P_values = [0, 1]
            D_values = [1]  # 季節性差分
            Q_values = [0, 1]
            
            # logging.info("🔍 正在進行自動參數選擇...")  # 註解掉 logging
            
            for p in p_values:
                for d in d_values:
                    for q in q_values:
                        for P in P_values:
                            for D in D_values:
                                for Q in Q_values:
                                    try:
                                        model = SARIMAX(historical_data,
                                                      order=(p, d, q),
                                                      seasonal_order=(P, D, Q, 12),
                                                      enforce_stationarity=False,
                                                      enforce_invertibility=False)
                                        
                                        results = model.fit(disp=False)
                                        
                                        # 計算綜合評分（AIC + BIC的加權平均）
                                        score = (results.aic + results.bic) / 2
                                        
                                        if score < best_aic:
                                            best_aic = score
                                            best_params = {
                                                'order': (p, d, q),
                                                'seasonal_order': (P, D, Q, 12),
                                                'enforce_stationarity': False,
                                                'enforce_invertibility': False
                                            }
                                            
                                    except Exception as e:
                                        # 忽略無法收斂的模型
                                        # logging.warning(f"嘗試參數 (p={p}, d={d}, q={q}, P={P}, D={D}, Q={Q}) 失敗: {e}")  # 註解掉 logging
                                        continue
            
            if best_params:
                # logging.info(f"✅ 最佳參數: SARIMA{best_params['order']}{best_params['seasonal_order']}")  # 註解掉 logging
                # logging.info(f"📊 最佳評分: {best_aic:.2f}")  # 註解掉 logging
                return best_params
            else:
                # logging.warning("⚠️ 無法找到合適的參數，使用預設參數")  # 註解掉 logging
                return self.model_params
                
        except Exception as e:
            # logging.error(f"自動參數選擇失敗: {e}")  # 註解掉 logging
            return self.model_params
    
    def _generate_detailed_chart(self, forecast_result):
        """生成細膩的預測圖表，確保與數據一致"""
        try:
            if not os.path.exists('static'):
                os.makedirs('static')
            
            # 獲取數據
            historical_data = np.array(forecast_result['historical_data']['data'])
            forecast_data = [item['forecast_sales'] for item in forecast_result['forecast_data']]
            date_labels = forecast_result['historical_data']['dates']
            forecast_dates = [item['period'] for item in forecast_result['forecast_data']]
            forecast_type = forecast_result['forecast_type']
            
            # 創建圖表
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # 設定樣式
            plt.rcParams['axes.unicode_minus'] = False
            plt.style.use('classic')
            plt.rcParams.update({
                'figure.facecolor': 'white',
                'axes.facecolor': 'white',
                'grid.color': '#E0E0E0',
                'grid.linestyle': '--',
                'grid.alpha': 0.7
            })
            
            # 繪製歷史數據
            if len(historical_data) > 0:
                ax.plot(range(len(historical_data)), 
                       historical_data, 
                       label='歷史數據', 
                       color='#4682B4',
                       linewidth=3,
                       marker='o',
                       markersize=6,
                       markerfacecolor='white',
                       markeredgewidth=2)
            
            # 繪製預測數據
            if len(historical_data) > 0:
                # 從歷史數據的末尾開始繪製預測數據
                ax.plot(range(len(historical_data), len(historical_data) + len(forecast_data)),
                       forecast_data,
                       label='預測數據',
                       color='#2E8B57',  # 改為綠色
                       linestyle='--',
                       linewidth=3,
                       marker='s',
                       markersize=6,
                       markerfacecolor='white',
                       markeredgewidth=2)
            else:
                ax.plot(range(len(forecast_data)),
                       forecast_data,
                       label='預測數據',
                       color='#2E8B57',  # 改為綠色
                       linestyle='--',
                       linewidth=3,
                       marker='s',
                       markersize=6,
                       markerfacecolor='white',
                       markeredgewidth=2)
            
            # 設定y軸範圍 - 固定從0開始，最高值600萬
            all_values = np.concatenate([historical_data, forecast_data]) if len(historical_data) > 0 else forecast_data
            min_val = 0  # x軸從0開始
            max_val = 6_000_000  # 最高值設定為600萬
            
            # 設定固定的y軸範圍
            ax.set_ylim(min_val, max_val)
            
            # 設定x軸標籤 - 調整間距讓波動看起來較小
            all_dates = date_labels + forecast_dates
            total_points = len(all_dates)
            
            # 根據數據點數調整間距 - 加大間隔
            if total_points <= 24:
                step = max(1, total_points // 6)  # 更少的標籤
            elif total_points <= 48:
                step = max(1, total_points // 8)  # 減少標籤數量
            else:
                step = max(1, total_points // 12)  # 較多數據時進一步減少標籤
                
            x_ticks = list(range(0, total_points, step))
            if total_points - 1 not in x_ticks:
                x_ticks.append(total_points - 1)
                
            ax.set_xticks(x_ticks)
            ax.set_xticklabels([all_dates[i] for i in x_ticks], rotation=45, ha='right')
            
            # 設定標題和標籤
            try:
                plt.rcParams['font.sans-serif'] = ['PingFang HK', 'STHeiti', 'Arial Unicode MS', 'SimHei', 'DejaVu Sans']
                ax.set_title(f'統一預測系統 - 銷售預測趨勢圖 ({forecast_type.capitalize()})', 
                            fontproperties=chinese_font, fontsize=16, pad=20)
                ax.set_xlabel('時間', fontproperties=chinese_font, fontsize=14)
                ax.set_ylabel('銷售金額 (NT$)', fontproperties=chinese_font, fontsize=14)
                legend = ax.legend(prop=chinese_font, loc='upper left', fontsize=12)
                
                for label in ax.get_xticklabels():
                    label.set_fontproperties(chinese_font)
                    
            except Exception as e:
                # logging.error(f"字型設定失敗，使用預設字型: {e}")  # 註解掉 logging
                ax.set_title(f'Unified Forecast System - Sales Forecast ({forecast_type.capitalize()})', fontsize=16, pad=20)
                ax.set_xlabel('Time', fontsize=14)
                ax.set_ylabel('Sales Amount (NT$)', fontsize=14)
                legend = ax.legend(loc='upper left', fontsize=12)
            
            # 添加網格 - 優化視覺效果
            ax.grid(True, linestyle='--', alpha=0.5, color='#E8E8E8')
            
            # 添加背景色以減少視覺波動
            ax.set_facecolor('#FAFAFA')
            
            # 設定y軸刻度 - 從0到600萬，每100萬一個刻度
            y_ticks = np.arange(0, max_val + 1, 1_000_000)
            ax.set_yticks(y_ticks)
            
            # 格式化y軸
            def format_amount(x, p):
                if x >= 1_000_000:
                    return f'{int(x/10000):,}萬'
                elif x >= 10000:
                    return f'{int(x/10000)}萬'
                else:
                    return f'{int(x):,}'
            
            ax.yaxis.set_major_formatter(plt.FuncFormatter(format_amount))
            
            # 設定y軸間隔 - 固定為100萬
            interval = 1_000_000
            ax.yaxis.set_major_locator(plt.MultipleLocator(interval))
            
            # 調整佈局
            plt.tight_layout()
            
            # 儲存圖表
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plot_path = f'static/unified_forecast_{timestamp}.png'
            plt.savefig(plot_path, bbox_inches='tight', dpi=300)
            plt.close()
            
            return {
                'chart_path': plot_path,
                'chart_filename': os.path.basename(plot_path)
            }
            
        except Exception as e:
            # logging.error(f"生成圖表時發生錯誤: {str(e)}")  # 註解掉 logging
            return {
                'chart_path': None,
                'chart_filename': None,
                'chart_error': str(e)
            }
    
    def _generate_comprehensive_ai_analysis(self, forecast_result):
        """生成全面的 AI 分析，包含詳細的預測解釋"""
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'API Key 未設定'
                }
            
            # 準備分析數據
            forecast_data = forecast_result['forecast_data']
            total_forecast = forecast_result['total_forecast']
            avg_forecast = forecast_result['avg_forecast']
            historical_stats = forecast_result['historical_data']['stats']
            
            # 分析趨勢
            sales_values = [item['forecast_sales'] for item in forecast_data]
            first_quarter_avg = sum(sales_values[:3]) / 3 if len(sales_values) >= 3 else avg_forecast
            last_quarter_avg = sum(sales_values[-3:]) / 3 if len(sales_values) >= 3 else avg_forecast
            trend_direction = "上升" if last_quarter_avg > first_quarter_avg else "下降"
            
            # 計算變異係數
            cv = np.std(sales_values) / np.mean(sales_values) if np.mean(sales_values) > 0 else 0
            
            # 生成詳細分析提示
            analysis_prompt = f"""
            作為資深經營分析專家，請對以下統一預測系統的銷售預測結果進行深入分析：

            【預測數據摘要】
            - 總預測銷售額：{total_forecast:,.0f} 元
            - 平均月銷售額：{avg_forecast:,.0f} 元
            - 預測期數：{len(forecast_data)} 個月
            - 整體趨勢：{trend_direction}
            - 變異係數：{cv:.2f}（衡量預測穩定性）

            【歷史數據統計】
            - 歷史數據點數：{historical_stats['data_points']} 個月
            - 總歷史銷售額：{historical_stats['total_sales']:,.0f} 元
            - 平均月銷售額：{historical_stats['avg_monthly_sales']:,.0f} 元
            - 歷史銷售標準差：{historical_stats['sales_std']:,.0f} 元

            【詳細預測數據】
            {chr(10).join([f"  • {item['period']}: {item['forecast_sales']:,.0f} 元" for item in forecast_data])}

            【模型資訊】
            - 模型類型：SARIMAX
            - 模型參數：ARIMA({forecast_result['model_info']['parameters']['order'][0]},{forecast_result['model_info']['parameters']['order'][1]},{forecast_result['model_info']['parameters']['order'][2]}) × SARIMA({forecast_result['model_info']['parameters']['seasonal_order'][0]},{forecast_result['model_info']['parameters']['seasonal_order'][1]},{forecast_result['model_info']['parameters']['seasonal_order'][2]},{forecast_result['model_info']['parameters']['seasonal_order'][3]})
            - AIC：{forecast_result['model_info']['model_summary']['aic']:.2f}
            - BIC：{forecast_result['model_info']['model_summary']['bic']:.2f}

            請提供以下分析：

            1. 【預測結果解釋】（300字以內）：
               - 預測結果的核心要點和關鍵發現
               - 與歷史數據的比較分析
               - 預測可信度評估

            2. 【趨勢分析】（400字以內）：
               - 銷售趨勢的季節性模式識別
               - 週期性變化的分析
               - 異常值或特殊模式的解釋

            3. 【業務策略建議】（500字以內）：
               - 基於預測結果的具體業務策略
               - 資源配置和預算規劃建議
               - 風險管理和應對措施

            4. 【績效監控指標】（200字以內）：
               - 關鍵績效指標（KPI）建議
               - 預測準確度監控方法
               - 預警機制設定

            5. 【資深經營分析專家報告】（600字以內）：
               - 綜合業務評估
               - 競爭優勢分析
               - 未來發展方向建議
               - 具體可執行的行動方案

            請以專業、客觀的語氣撰寫，並提供具體可執行的建議。重點解釋預測結果的合理性，以及如何基於這些預測制定有效的業務策略。
            """
            
            # 調用 Gemini API
            headers = {
                'Content-Type': 'application/json',
            }
            
            data = {
                'contents': [{
                    'parts': [{
                        'text': analysis_prompt
                    }]
                }]
            }
            
            response = requests.post(
                f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={self.api_key}',
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    analysis_text = result['candidates'][0]['content']['parts'][0]['text']
                    return {
                        'success': True,
                        'analysis': analysis_text,
                        'timestamp': datetime.now().isoformat(),
                        'analysis_metadata': {
                            'total_forecast': safe_float(total_forecast),
                            'avg_forecast': safe_float(avg_forecast),
                            'trend_direction': trend_direction,
                            'variation_coefficient': safe_float(cv),
                            'forecast_periods': len(forecast_data)
                        }
                    }
                else:
                    return {
                        'success': False,
                        'error': 'AI 回應格式錯誤'
                    }
            else:
                return {
                    'success': False,
                    'error': f'API 請求失敗: {response.status_code}'
                }
                
        except Exception as e:
            # logging.error(f"AI 分析失敗: {str(e)}")  # 註解掉 logging
            return {
                'success': False,
                'error': f'AI 分析失敗: {str(e)}'
            }
    
    def _get_historical_data(self):
        """獲取歷史數據，使用與原始預測系統相同的查詢方式"""
        try:
            # 使用與原始預測系統相同的查詢
            query = """
                SELECT 
                    t.year,
                    t.month,
                    COALESCE(SUM(f.amount), 0) as monthly_sales
                FROM sales_fact f
                JOIN dim_time t ON f.time_id = t.time_id
                GROUP BY t.year, t.month
                ORDER BY t.year, t.month
            """
            
            result = self.db_manager.execute_query(query)
            
            if result.empty:
                raise Exception("資料庫查詢返回空結果")
            
            data = result.values.tolist()
            
            if not data:
                # logging.warning("⚠️ 沒有找到歷史銷售數據，使用示例數據")  # 註解掉 logging
                # 返回示例數據
                return [1000000, 1200000, 1100000, 1300000, 1250000, 1400000], ['2022/01', '2022/02', '2022/03', '2022/04', '2022/05', '2022/06']
            
            # 轉換為時間序列格式
            sales_data = []
            date_labels = []
            
            for row in data:
                year = int(row[0])
                month = int(row[1])
                sales = safe_float(row[2])
                date_label = f"{year}/{month:02d}"
                
                sales_data.append(sales)
                date_labels.append(date_label)
            
            # logging.info(f"📊 成功獲取歷史數據：{len(sales_data)} 個數據點")  # 註解掉 logging
            # logging.info(f"📅 訓練期間：{date_labels[0]} 到 {date_labels[-1]}")  # 註解掉 logging
            
            return sales_data, date_labels
            
        except Exception as e:
            # logging.error(f"獲取歷史數據失敗: {str(e)}")  # 註解掉 logging
            # 返回示例數據
            return [1000000, 1200000, 1100000, 1300000, 1250000, 1400000], ['2022/01', '2022/02', '2022/03', '2022/04', '2022/05', '2022/06']
    
    def _process_forecast_results(self, forecast, forecast_type, periods, forecast_dates):
        """處理預測結果"""
        forecast_data = []
        
        for i, (date, value) in enumerate(zip(forecast_dates, forecast)):
            forecast_data.append({
                'period': date,
                'forecast_sales': safe_float(value)
            })
        
        return forecast_data
    
    def _generate_forecast_summary(self, forecast_type, periods, total_forecast, avg_forecast, forecast_data, historical_stats):
        """生成預測摘要"""
        try:
            # 根據預測類型生成摘要
            period_text_map = {
                'month': '月',
                'quarter': '季', 
                'year': '年'
            }
            period_text = period_text_map.get(forecast_type, '月')
            
            # 計算增長率
            historical_avg = historical_stats.get('avg_monthly_sales', 0)
            if historical_avg > 0:
                growth_rate = ((avg_forecast - historical_avg) / historical_avg) * 100
            else:
                growth_rate = 0
            
            # 生成摘要內容
            summary_parts = []
            summary_parts.append(f"## {period_text}度業績預測分析報告")
            summary_parts.append("")
            summary_parts.append(f"### 預測概況")
            summary_parts.append(f"- **預測期間**: 未來 {periods} {period_text}")
            summary_parts.append(f"- **總預測銷售額**: {total_forecast:,.2f} 元")
            summary_parts.append(f"- **平均{period_text}度銷售額**: {avg_forecast:,.2f} 元")
            summary_parts.append(f"- **歷史平均{period_text}度銷售額**: {historical_avg:,.2f} 元")
            summary_parts.append("")
            
            # 趨勢分析
            summary_parts.append(f"### 趨勢分析")
            if growth_rate > 5:
                summary_parts.append(f"- 預測顯示{period_text}度銷售額呈上升趨勢")
                summary_parts.append(f"- 平均每{period_text}預計增長 {growth_rate:.2f}%")
            elif growth_rate < -5:
                summary_parts.append(f"- 預測顯示{period_text}度銷售額呈下降趨勢")
                summary_parts.append(f"- 平均每{period_text}預計下降 {abs(growth_rate):.2f}%")
            else:
                summary_parts.append(f"- 預測顯示{period_text}度銷售額保持穩定")
            
            summary_parts.append("")
            summary_parts.append(f"### 預測數據")
            for i, item in enumerate(forecast_data[:6]):  # 只顯示前6個
                summary_parts.append(f"- {item['period']}: {item['forecast_sales']:,.2f} 元")
            if len(forecast_data) > 6:
                summary_parts.append(f"- ... 共 {len(forecast_data)} 個預測期間")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            # logging.error(f"生成預測摘要失敗: {e}")  # 註解掉 logging
            return f"預測摘要生成失敗: {str(e)}" 