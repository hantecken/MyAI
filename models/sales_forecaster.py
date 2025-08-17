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
warnings.filterwarnings('ignore')

# 設定中文字型
# macOS 系統自帶的中文字型
font_paths = [
    '/System/Library/Fonts/PingFang.ttc',  # PingFang 字型
    '/System/Library/Fonts/STHeiti Light.ttc',  # 黑體字型
    '/System/Library/Fonts/Hiragino Sans GB.ttc',  # 冬青黑體
    '/System/Library/Fonts/Arial Unicode MS.ttf',  # Arial Unicode
    '/System/Library/Fonts/Helvetica.ttc'  # Helvetica
]

# 尋找可用的中文字型
chinese_font = None
try:
    for font_path in font_paths:
        if os.path.exists(font_path):
            chinese_font = FontProperties(fname=font_path)
            print(f"成功載入字型: {font_path}")
            break
    
    # 如果找不到中文字型，嘗試使用 matplotlib 內建字型
    if chinese_font is None:
        import matplotlib.font_manager as fm
        # 尋找支援中文的字型
        chinese_fonts = [f.name for f in fm.fontManager.ttflist if 'chinese' in f.name.lower() or 'cjk' in f.name.lower()]
        if chinese_fonts:
            chinese_font = FontProperties(family=chinese_fonts[0])
            print(f"使用內建中文字型: {chinese_fonts[0]}")
        else:
            chinese_font = FontProperties()
            print("使用預設字型")
except Exception as e:
    print(f"字型設定錯誤: {e}")
    chinese_font = FontProperties()

class SalesForecaster:
    """
    銷售預測器類，負責處理所有預測相關功能
    """
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.default_periods = 12
        self.default_seasonal_periods = 12  # 月度資料的季節性週期

    def forecast_sales(self, forecast_type='month', periods=12):
        """
        生成銷售預測
        Args:
            forecast_type: 預測類型 ('month', 'quarter', 'year')
            periods: 預測期數
        Returns:
            dict: 包含預測結果的字典
        """
        try:
            # 從資料庫獲取歷史數據
            historical_data, date_labels = self._get_historical_data()
            
            # 資料預處理
            historical_data = pd.Series(historical_data)
            
            # 確保數據是固定頻率的時間序列
            historical_data = historical_data.astype(float)
            
            # 保存原始數據用於圖表生成
            historical_data_for_plot = historical_data.values
            
            # 使用SARIMAX模型進行預測
            model = SARIMAX(historical_data,
                          order=(1, 1, 1),
                          seasonal_order=(1, 1, 1, 12),
                          enforce_stationarity=False,
                          enforce_invertibility=False)
            
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
            
            # 生成預測圖表
            plot_path = self._generate_forecast_plot(historical_data_for_plot, forecast, forecast_type,
                                                   date_labels, forecast_dates)
            
            # 如果圖表生成失敗，設定為 None
            if plot_path is None:
                plot_path = None
            
            # 計算預測時間範圍
            forecast_range = f"{forecast_dates[0]} - {forecast_dates[-1]}"
            
            # 準備歷史數據用於圖表
            historical_data_for_chart = []
            for i, (date_label, sales_value) in enumerate(zip(date_labels, historical_data)):
                historical_data_for_chart.append({
                    'period': date_label,
                    'sales': float(sales_value)
                })
            
            return {
                'success': True,
                'forecast_data': forecast_data,
                'historical_data': historical_data_for_chart,  # 添加歷史數據
                'total_forecast': total_forecast,
                'avg_forecast': avg_forecast,
                'plot_path': plot_path,
                'model_info': {
                    'aic': results.aic,
                    'method': 'SARIMAX',
                    'forecast_range': forecast_range,
                    'historical_data_points': len(historical_data),
                    'prediction_date': datetime.now().strftime("%Y-%m-%d"),
                    'parameters': {
                        'order': (1, 1, 1),
                        'seasonal_order': (1, 1, 1, 12)
                    },
                    'training_period': {
                        'start': date_labels[0],
                        'end': date_labels[-1]
                    }
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _get_historical_data(self):
        """
        從資料庫獲取歷史銷售數據，按月份匯總
        Returns:
            tuple: (銷售數據陣列, 日期標籤陣列)
        """
        try:
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
                raise ValueError("無法獲取歷史銷售數據")
            
            # 生成日期標籤
            date_labels = []
            for _, row in result.iterrows():
                year = int(row['year'])
                month = int(row['month'])
                date_labels.append(f"{year}/{month:02d}")
            
            # 轉換銷售數據為 numpy array
            sales_data = result['monthly_sales'].to_numpy()
            
            return sales_data, date_labels
        except Exception as e:
            raise ValueError(f"獲取歷史數據時發生錯誤：{str(e)}")

    def _process_forecast_results(self, forecast, forecast_type, periods, forecast_dates):
        """
        處理預測結果
        Args:
            forecast: 預測數據
            forecast_type: 預測類型 ('month', 'quarter', 'year')
            periods: 預測期數
            forecast_dates: 預測期間的日期標籤列表
        Returns:
            list: 處理後的預測結果
        """
        if forecast_type == 'month':
            return [{'period': forecast_dates[i], 'forecast_sales': v} 
                    for i, v in enumerate(forecast[:periods])]
        elif forecast_type == 'quarter':
            quarterly_data = []
            for i in range(0, len(forecast), 3):
                if len(quarterly_data) >= periods:
                    break
                quarter_sum = sum(forecast[i:i+3])
                quarter_start = forecast_dates[i]
                quarter_year = quarter_start.split('/')[0]
                quarter_num = ((int(quarter_start.split('/')[1]) - 1) // 3) + 1
                quarterly_data.append({
                    'period': f'{quarter_year} Q{quarter_num}',
                    'forecast_sales': quarter_sum
                })
            return quarterly_data
        else:  # year
            yearly_data = []
            for i in range(0, len(forecast), 12):
                if len(yearly_data) >= periods:
                    break
                year_sum = sum(forecast[i:i+12])
                year = forecast_dates[i].split('/')[0]
                yearly_data.append({
                    'period': year,
                    'forecast_sales': year_sum
                })
            return yearly_data

    def _generate_forecast_plot(self, historical_data, forecast, forecast_type, date_labels, forecast_dates):
        """
        生成預測圖表
        Args:
            historical_data: 歷史數據
            forecast: 預測數據
            forecast_type: 預測類型 ('month', 'quarter', 'year')
            date_labels: 歷史數據的日期標籤
            forecast_dates: 預測期間的日期標籤
        Returns:
            str: 圖表檔案路徑
        """
        try:
            # 確保 static 目錄存在
            if not os.path.exists('static'):
                os.makedirs('static')
            
            plt.figure(figsize=(12, 6))
            
            # 設定 plt 字型和樣式
            plt.rcParams['axes.unicode_minus'] = False  # 解決負號顯示問題
            plt.style.use('classic')  # 使用經典樣式
            
            # 設定自定義樣式
            plt.rcParams.update({
                'figure.facecolor': 'white',
                'axes.facecolor': 'white',
                'grid.color': '#E0E0E0',
                'grid.linestyle': '--',
                'grid.alpha': 0.7
            })
            
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # 計算y軸的合適範圍
            if len(historical_data) > 0:
                # 確保 historical_data 是 numpy array
                hist_data = np.array(historical_data)
                all_values = np.concatenate([hist_data, forecast])
            else:
                all_values = forecast
            min_val = np.min(all_values)
            max_val = np.max(all_values)
            y_margin = (max_val - min_val) * 0.1  # 增加10%的邊距
            
            # 繪製歷史數據
            if len(historical_data) > 0:
                # 確保 historical_data 是 numpy array
                hist_data = np.array(historical_data)
                ax.plot(range(len(hist_data)), 
                       hist_data, 
                       label='歷史數據', 
                       color='#4682B4',  # 使用鋼青色
                       linewidth=2,
                       marker='o',
                       markersize=4,
                       markerfacecolor='white')
            
            # 繪製預測數據
            if len(historical_data) > 0:
                # 確保 historical_data 是 numpy array
                hist_data = np.array(historical_data)
                ax.plot(range(len(hist_data)-1, len(hist_data) + len(forecast)),
                       [hist_data[-1]] + list(forecast),
                       label='預測數據',
                       color='#CD5C5C',  # 使用印度紅色
                       linestyle='--',
                       linewidth=2,
                       marker='s',
                       markersize=4,
                       markerfacecolor='white')
            else:
                # 如果沒有歷史數據，只繪製預測數據
                ax.plot(range(len(forecast)),
                       forecast,
                       label='預測數據',
                       color='#CD5C5C',  # 使用印度紅色
                       linestyle='--',
                       linewidth=2,
                       marker='s',
                       markersize=4,
                       markerfacecolor='white')
            
            # 設定y軸範圍為0-600萬
            ax.set_ylim(0, 6_000_000)
            
            # 設定x軸標籤
            x_positions = np.arange(len(date_labels) + len(forecast_dates))
            all_dates = date_labels + forecast_dates
            
            # 設定x軸刻度和標籤
            step = max(1, len(all_dates) // 12)  # 確保不會顯示太多標籤
            
            # 確保至少顯示開始、中間和結束的日期
            x_ticks = list(range(0, len(all_dates), step))
            if len(all_dates) - 1 not in x_ticks:
                x_ticks.append(len(all_dates) - 1)
                
            ax.set_xticks(x_ticks)
            ax.set_xticklabels([all_dates[i] for i in x_ticks], rotation=45, ha='right')
            
            # 使用中文字型設定標題和標籤
            try:
                # 設定全域字型
                plt.rcParams['font.sans-serif'] = ['PingFang HK', 'STHeiti', 'Arial Unicode MS', 'SimHei', 'DejaVu Sans']
                plt.rcParams['axes.unicode_minus'] = False
                
                ax.set_title(f'銷售預測 ({forecast_type.capitalize()})', 
                            fontproperties=chinese_font, fontsize=14, pad=15)
                ax.set_xlabel('時間', fontproperties=chinese_font, fontsize=12)
                ax.set_ylabel('銷售金額 (NT$)', fontproperties=chinese_font, fontsize=12)
                
                # 設定圖例
                legend = ax.legend(prop=chinese_font, loc='upper left')
                
                # 設定 x 軸標籤字型
                ax.tick_params(axis='x', labelsize=10)
                for label in ax.get_xticklabels():
                    label.set_fontproperties(chinese_font)
                    
            except Exception as e:
                print(f"字型設定失敗，使用預設字型: {e}")
                # 使用預設字型
                ax.set_title(f'Sales Forecast ({forecast_type.capitalize()})', fontsize=14, pad=15)
                ax.set_xlabel('Time', fontsize=12)
                ax.set_ylabel('Sales Amount (NT$)', fontsize=12)
                legend = ax.legend(loc='upper left')
            
            # 添加網格，但使用更淺的顏色
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # 格式化y軸刻度標籤
            def format_amount(x, p):
                if x >= 1_000_000:
                    return f'{int(x/10000):,}萬'
                elif x >= 10000:
                    return f'{int(x/10000)}萬'
                else:
                    return f'{int(x):,}'
            
            ax.yaxis.set_major_formatter(plt.FuncFormatter(format_amount))
            
            # 設定y軸主要刻度間隔
            if len(historical_data) > 0:
                # 確保 historical_data 是 numpy array
                hist_data = np.array(historical_data)
                max_value = max(max(hist_data), max(forecast))
            else:
                max_value = max(forecast)
            if max_value > 5_000_000:
                interval = 1_000_000  # 每100萬
            elif max_value > 1_000_000:
                interval = 500_000    # 每50萬
            else:
                interval = 100_000    # 每10萬
            
            ax.yaxis.set_major_locator(plt.MultipleLocator(interval))
            
            # 調整圖表邊距，確保x軸標籤不會被切掉
            plt.tight_layout()
            
            # 儲存圖表
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plot_path = f'static/forecast_{timestamp}.png'
            plt.savefig(plot_path, bbox_inches='tight', dpi=300)
            plt.close()
            
            return plot_path
            
        except Exception as e:
            print(f"生成圖表時發生錯誤: {str(e)}")
            import traceback
            print(f"詳細錯誤信息: {traceback.format_exc()}")
            # 返回一個預設的錯誤路徑，而不是拋出異常
            return None
