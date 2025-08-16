"""
預測停止條件模組
提供基於週期性考量的預測停止策略
"""

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import acf
from scipy.signal import find_peaks
import warnings
warnings.filterwarnings('ignore')


class ForecastStopCriteria:
    """
    預測停止條件評估器
    """
    
    def __init__(self, data, seasonal_period=12):
        """
        初始化預測停止條件評估器
        
        Parameters:
        -----------
        data : array-like
            時間序列數據
        seasonal_period : int
            季節性週期，預設為12（月度數據）
        """
        self.data = np.array(data)
        self.seasonal_period = seasonal_period
        self.stop_reasons = []
        self.warnings = []
    
    def check_data_sufficiency(self, min_periods=24):
        """
        檢查數據充足性
        
        Parameters:
        -----------
        min_periods : int
            最少需要的數據點數
            
        Returns:
        --------
        bool : 數據是否充足
        """
        if len(self.data) < min_periods:
            self.stop_reasons.append(f"歷史數據不足，建議至少{min_periods}個數據點")
            return False
        return True
    
    def check_seasonal_stability(self, strength_threshold=0.1, variance_ratio=2.0):
        """
        檢查季節性穩定性
        
        Parameters:
        -----------
        strength_threshold : float
            季節性強度閾值
        variance_ratio : float
            季節性方差與趨勢方差的比例閾值
            
        Returns:
        --------
        tuple : (是否穩定, 訊息)
        """
        try:
            # 季節性分解
            decomposition = seasonal_decompose(self.data, period=self.seasonal_period)
            
            # 計算季節性強度
            seasonal_strength = np.abs(decomposition.seasonal).sum() / np.abs(self.data).sum()
            
            # 檢查季節性強度
            if seasonal_strength < strength_threshold:
                return False, f"季節性不明顯 (強度: {seasonal_strength:.3f})，建議使用非季節性模型"
            
            # 檢查季節性穩定性
            seasonal_variance = np.var(decomposition.seasonal)
            trend_variance = np.var(decomposition.trend[~np.isnan(decomposition.trend)])
            
            if seasonal_variance > trend_variance * variance_ratio:
                return False, f"季節性變化過大 (方差比: {seasonal_variance/trend_variance:.2f})"
            
            return True, f"季節性穩定 (強度: {seasonal_strength:.3f})"
            
        except Exception as e:
            return False, f"季節性分析失敗: {str(e)}"
    
    def check_forecast_error(self, actual, predicted, mape_threshold=15.0, trend_stability_threshold=0.1):
        """
        檢查預測誤差
        
        Parameters:
        -----------
        actual : array-like
            實際值
        predicted : array-like
            預測值
        mape_threshold : float
            MAPE閾值（百分比）
        trend_stability_threshold : float
            趨勢穩定性閾值
            
        Returns:
        --------
        tuple : (是否可接受, 訊息)
        """
        actual = np.array(actual)
        predicted = np.array(predicted)
        
        # 計算MAPE
        mape = np.mean(np.abs((actual - predicted) / actual)) * 100
        
        if mape > mape_threshold:
            return False, f"預測誤差過大 (MAPE: {mape:.2f}%)"
        
        # 計算預測趨勢穩定性
        trend_stability = np.std(np.diff(predicted)) / np.mean(predicted)
        
        if trend_stability > trend_stability_threshold:
            return False, f"預測趨勢不穩定 (穩定性: {trend_stability:.3f})"
        
        return True, f"預測穩定 (MAPE: {mape:.2f}%)"
    
    def check_business_cycle(self, cycle_period=None):
        """
        檢查業務週期穩定性
        
        Parameters:
        -----------
        cycle_period : int, optional
            業務週期長度，如果為None則自動檢測
            
        Returns:
        --------
        tuple : (是否穩定, 訊息)
        """
        if cycle_period is None:
            cycle_period = self.seasonal_period
        
        try:
            # 找到週期峰值
            peaks, _ = find_peaks(self.data, distance=cycle_period//2)
            
            if len(peaks) < 2:
                return True, "數據不足以檢測業務週期"
            
            # 計算週期穩定性
            cycle_lengths = np.diff(peaks)
            cycle_stability = np.std(cycle_lengths) / np.mean(cycle_lengths)
            
            if cycle_stability > 0.3:
                return False, f"業務週期不穩定 (變異係數: {cycle_stability:.3f})"
            
            return True, f"業務週期穩定 (變異係數: {cycle_stability:.3f})"
            
        except Exception as e:
            return False, f"業務週期分析失敗: {str(e)}"
    
    def detect_multiple_periods(self):
        """
        檢測多個週期
        
        Returns:
        --------
        dict : 檢測到的週期信息
        """
        periods = {
            'daily': 1,
            'weekly': 7,
            'monthly': 30,
            'quarterly': 90,
            'yearly': 365
        }
        
        detected_periods = {}
        
        for period_name, period_length in periods.items():
            try:
                # 使用自相關函數檢測週期
                acf_values = acf(self.data, nlags=min(period_length*2, len(self.data)//2))
                
                # 找到顯著的週期
                significant_lags = np.where(acf_values > 0.5)[0]
                
                if len(significant_lags) > 0:
                    detected_periods[period_name] = {
                        'period': period_length,
                        'strength': np.max(acf_values[significant_lags])
                    }
            except:
                continue
        
        return detected_periods
    
    def check_forecast_horizon(self, forecast_horizon=12):
        """
        檢查預測週期是否合理
        
        Parameters:
        -----------
        forecast_horizon : int
            預測週期長度
            
        Returns:
        --------
        tuple : (是否合理, 訊息)
        """
        detected_periods = self.detect_multiple_periods()
        
        if detected_periods:
            # 選擇最強的週期
            strongest_period = max(detected_periods.items(), 
                                 key=lambda x: x[1]['strength'])
            
            # 檢查週期強度
            if strongest_period[1]['strength'] < 0.3:
                return False, "週期性不明顯，建議停止預測"
            
            # 檢查預測週期是否合理
            max_reasonable_period = strongest_period[1]['period'] * 3
            if forecast_horizon > max_reasonable_period:
                return False, f"預測週期過長，建議不超過 {max_reasonable_period} 期"
        
        return True, "預測週期合理"
    
    def auto_sarima_stop_criteria(self, max_p=3, max_d=2, max_q=3, max_P=2, max_D=1, max_Q=2):
        """
        SARIMA模型自動參數選擇的停止條件
        
        Parameters:
        -----------
        max_p, max_d, max_q : int
            非季節性參數的最大值
        max_P, max_D, max_Q : int
            季節性參數的最大值
            
        Returns:
        --------
        tuple : (最佳參數, 最佳AIC)
        """
        best_aic = float('inf')
        best_params = None
        
        for p in range(max_p + 1):
            for d in range(max_d + 1):
                for q in range(max_q + 1):
                    for P in range(max_P + 1):
                        for D in range(max_D + 1):
                            for Q in range(max_Q + 1):
                                try:
                                    model = SARIMAX(self.data, 
                                                  order=(p, d, q), 
                                                  seasonal_order=(P, D, Q, self.seasonal_period))
                                    fitted_model = model.fit(disp=False)
                                    
                                    # 停止條件1: AIC改善小於閾值
                                    if fitted_model.aic < best_aic - 0.01:
                                        best_aic = fitted_model.aic
                                        best_params = (p, d, q, P, D, Q)
                                    
                                    # 停止條件2: 模型收斂檢查
                                    if fitted_model.mle_retvals['converged']:
                                        break
                                        
                                except:
                                    continue
        
        return best_params, best_aic
    
    def comprehensive_check(self, forecast_horizon=12, min_periods=24):
        """
        綜合預測停止檢查
        
        Parameters:
        -----------
        forecast_horizon : int
            預測週期長度
        min_periods : int
            最少需要的數據點數
            
        Returns:
        --------
        tuple : (是否可預測, 停止原因列表)
        """
        self.stop_reasons = []
        self.warnings = []
        
        # 1. 數據充足性檢查
        if not self.check_data_sufficiency(min_periods):
            return False, self.stop_reasons
        
        # 2. 季節性穩定性檢查
        seasonal_ok, seasonal_msg = self.check_seasonal_stability()
        if not seasonal_ok:
            self.stop_reasons.append(seasonal_msg)
        else:
            self.warnings.append(seasonal_msg)
        
        # 3. 業務週期檢查
        business_ok, business_msg = self.check_business_cycle()
        if not business_ok:
            self.stop_reasons.append(business_msg)
        else:
            self.warnings.append(business_msg)
        
        # 4. 預測週期合理性檢查
        horizon_ok, horizon_msg = self.check_forecast_horizon(forecast_horizon)
        if not horizon_ok:
            self.stop_reasons.append(horizon_msg)
        else:
            self.warnings.append(horizon_msg)
        
        return len(self.stop_reasons) == 0, self.stop_reasons
    
    def get_dynamic_forecast_period(self, base_period=12):
        """
        根據數據特性動態調整預測週期
        
        Parameters:
        -----------
        base_period : int
            基礎預測週期
            
        Returns:
        --------
        int : 調整後的預測週期
        """
        detected_periods = self.detect_multiple_periods()
        
        if detected_periods:
            # 根據最強週期調整預測週期
            strongest_period = max(detected_periods.items(), 
                                 key=lambda x: x[1]['strength'])
            
            # 預測週期不超過3個完整週期
            adjusted_period = min(base_period, strongest_period[1]['period'] * 3)
            
            return adjusted_period
        
        return base_period
    
    def monitor_forecast_quality(self, actual, predicted, threshold=0.2):
        """
        監控預測質量
        
        Parameters:
        -----------
        actual : array-like
            實際值
        predicted : array-like
            預測值
        threshold : float
            警報閾值
            
        Returns:
        --------
        list : 警報列表
        """
        actual = np.array(actual)
        predicted = np.array(predicted)
        
        alerts = []
        
        # 計算MAPE
        mape = np.mean(np.abs((actual - predicted) / actual)) * 100
        
        if mape > threshold * 100:
            alerts.append(f"MAPE過高: {mape:.2f}%")
        
        # 計算RMSE
        rmse = np.sqrt(np.mean((actual - predicted) ** 2))
        
        if rmse > np.std(actual) * 0.5:
            alerts.append(f"RMSE過高: {rmse:.2f}")
        
        return alerts
    
    def seasonal_change_alert(self, window=12):
        """
        檢測季節性變化並發出警報
        
        Parameters:
        -----------
        window : int
            滾動窗口大小
            
        Returns:
        --------
        str or None : 警報訊息
        """
        if len(self.data) < window * 2:
            return None
        
        seasonal_strengths = []
        
        for i in range(window, len(self.data)):
            window_data = self.data[i-window:i]
            try:
                strength_ok, _ = self.check_seasonal_stability()
                seasonal_strengths.append(1 if strength_ok else 0)
            except:
                seasonal_strengths.append(0)
        
        # 檢測季節性強度變化
        if len(seasonal_strengths) > 1:
            strength_change = np.std(seasonal_strengths)
            
            if strength_change > 0.1:
                return f"季節性強度變化過大: {strength_change:.3f}"
        
        return None


def create_forecast_stop_criteria(data, seasonal_period=12):
    """
    創建預測停止條件評估器的便捷函數
    
    Parameters:
    -----------
    data : array-like
        時間序列數據
    seasonal_period : int
        季節性週期
        
    Returns:
    --------
    ForecastStopCriteria : 預測停止條件評估器實例
    """
    return ForecastStopCriteria(data, seasonal_period) 