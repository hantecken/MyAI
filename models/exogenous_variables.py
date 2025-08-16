"""
外生變數管理器 - 用於 SARIMAX 模型
"""
import pandas as pd
from datetime import datetime
import numpy as np

class ExogenousVariables:
    def __init__(self):
        # 固定節慶日期（使用月-日格式）
        self.festivals = {
            # 西曆固定節日
            'new_year': '01-01',
            'valentine': '02-14',
            'christmas': '12-25',
            'new_year_eve': '12-31',
            
            # 每年更新的農曆節日 (需要另外更新)
            'chinese_new_year': [],  # [('2024-02-10', '2024-02-17'), ('2025-01-29', '2025-02-05')]
            'dragon_boat': [],       # [('2024-06-10'), ('2025-05-31')]
            'mid_autumn': []         # [('2024-09-17'), ('2025-09-06')]
        }
        
        # 促銷活動資料結構
        self.promotions = {
            'monthly_sale': [],     # 每月促銷日
            'special_events': [],   # 特殊促銷活動
            'member_day': []        # 會員日
        }
    
    def get_festival_indicators(self, date_series):
        """
        產生節慶指標
        0: 非節慶
        1: 節慶期間
        0.5: 節慶前後一週
        """
        indicators = pd.DataFrame(index=date_series)
        
        # 處理固定節日
        for date in date_series:
            month_day = date.strftime('%m-%d')
            
            # 初始化指標
            festival_indicator = 0
            
            # 檢查是否在固定節日清單中
            if month_day in self.festivals.values():
                festival_indicator = 1
            
            # 檢查是否在農曆節日期間
            for festival_dates in self.festivals.values():
                if isinstance(festival_dates, list):
                    for period in festival_dates:
                        if isinstance(period, tuple):
                            start_date = datetime.strptime(period[0], '%Y-%m-%d')
                            end_date = datetime.strptime(period[1], '%Y-%m-%d')
                            if start_date <= date <= end_date:
                                festival_indicator = 1
                                break
            
            indicators.loc[date, 'festival'] = festival_indicator
        
        return indicators

    def get_promotion_indicators(self, date_series):
        """
        產生促銷活動指標
        0: 非促銷
        1: 促銷期間
        0.5: 促銷開始前三天
        """
        indicators = pd.DataFrame(index=date_series)
        indicators['promotion'] = 0
        
        for date in date_series:
            # 檢查是否在促銷期間
            if any(start <= date <= end for start, end in self.promotions['monthly_sale']):
                indicators.loc[date, 'promotion'] = 1
            elif any(start <= date <= end for start, end in self.promotions['special_events']):
                indicators.loc[date, 'promotion'] = 1
            elif date.strftime('%d') in self.promotions['member_day']:
                indicators.loc[date, 'promotion'] = 1
        
        return indicators

    def prepare_exogenous_variables(self, date_series):
        """
        準備所有外生變數
        返回包含所有指標的 DataFrame
        """
        # 合併節慶和促銷指標
        festival_indicators = self.get_festival_indicators(date_series)
        promotion_indicators = self.get_promotion_indicators(date_series)
        
        # 合併所有指標
        exog_variables = pd.concat([festival_indicators, promotion_indicators], axis=1)
        
        # 填補遺失值
        exog_variables = exog_variables.fillna(0)
        
        return exog_variables

    def update_festival_dates(self, year, festival_dates):
        """
        更新農曆節日日期
        festival_dates: {
            'chinese_new_year': [('2024-02-10', '2024-02-17')],
            'dragon_boat': ['2024-06-10'],
            'mid_autumn': ['2024-09-17']
        }
        """
        for festival, dates in festival_dates.items():
            if festival in self.festivals:
                self.festivals[festival] = dates

    def add_promotion(self, promotion_type, dates):
        """
        新增促銷活動
        promotion_type: 'monthly_sale', 'special_events', 'member_day'
        dates: 對應的日期列表或元組
        """
        if promotion_type in self.promotions:
            self.promotions[promotion_type].extend(dates)
