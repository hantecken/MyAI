"""
預測停止條件使用範例
展示如何使用週期性考量的預測停止策略
"""

import numpy as np
import pandas as pd
# import matplotlib.pyplot as plt  # 暫時註釋掉
from statsmodels.tsa.statespace.sarimax import SARIMAX
import sys
import os

# 添加父目錄到路徑以導入模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.forecast_stop_criteria import ForecastStopCriteria, create_forecast_stop_criteria


def generate_sample_data(n_periods=60, seasonal_period=12):
    """
    生成範例時間序列數據
    """
    np.random.seed(42)
    
    # 基礎趨勢
    trend = np.linspace(100, 150, n_periods)
    
    # 季節性成分
    seasonal = 20 * np.sin(2 * np.pi * np.arange(n_periods) / seasonal_period)
    
    # 隨機噪聲
    noise = np.random.normal(0, 5, n_periods)
    
    # 組合數據
    data = trend + seasonal + noise
    
    return data


def example_basic_usage():
    """
    基本使用範例
    """
    print("=== 基本使用範例 ===")
    
    # 生成範例數據
    data = generate_sample_data(60, 12)
    
    # 創建預測停止條件評估器
    stop_criteria = ForecastStopCriteria(data, seasonal_period=12)
    
    # 進行綜合檢查
    can_forecast, stop_reasons = stop_criteria.comprehensive_check(
        forecast_horizon=12, 
        min_periods=24
    )
    
    print(f"是否可以進行預測: {can_forecast}")
    if stop_reasons:
        print("停止原因:")
        for reason in stop_reasons:
            print(f"  - {reason}")
    
    # 獲取動態預測週期
    dynamic_period = stop_criteria.get_dynamic_forecast_period(base_period=12)
    print(f"建議的預測週期: {dynamic_period}")
    
    # 檢測多個週期
    detected_periods = stop_criteria.detect_multiple_periods()
    print("檢測到的週期:")
    for period_name, period_info in detected_periods.items():
        print(f"  - {period_name}: 強度 {period_info['strength']:.3f}")


def example_seasonal_analysis():
    """
    季節性分析範例
    """
    print("\n=== 季節性分析範例 ===")
    
    # 生成具有強季節性的數據
    data = generate_sample_data(60, 12)
    
    stop_criteria = ForecastStopCriteria(data, seasonal_period=12)
    
    # 檢查季節性穩定性
    seasonal_ok, seasonal_msg = stop_criteria.check_seasonal_stability()
    print(f"季節性檢查結果: {seasonal_msg}")
    
    # 檢查業務週期
    business_ok, business_msg = stop_criteria.check_business_cycle()
    print(f"業務週期檢查結果: {business_msg}")
    
    # 檢查預測週期合理性
    horizon_ok, horizon_msg = stop_criteria.check_forecast_horizon(forecast_horizon=12)
    print(f"預測週期檢查結果: {horizon_msg}")


def example_forecast_quality_monitoring():
    """
    預測質量監控範例
    """
    print("\n=== 預測質量監控範例 ===")
    
    # 生成實際值和預測值
    actual = generate_sample_data(30, 12)
    predicted = actual + np.random.normal(0, 3, 30)  # 添加一些預測誤差
    
    stop_criteria = ForecastStopCriteria(actual, seasonal_period=12)
    
    # 檢查預測誤差
    error_ok, error_msg = stop_criteria.check_forecast_error(actual, predicted)
    print(f"預測誤差檢查: {error_msg}")
    
    # 監控預測質量
    alerts = stop_criteria.monitor_forecast_quality(actual, predicted)
    if alerts:
        print("預測質量警報:")
        for alert in alerts:
            print(f"  - {alert}")
    else:
        print("預測質量良好")


def example_sarima_parameter_optimization():
    """
    SARIMA參數優化範例
    """
    print("\n=== SARIMA參數優化範例 ===")
    
    data = generate_sample_data(60, 12)
    stop_criteria = ForecastStopCriteria(data, seasonal_period=12)
    
    # 自動參數選擇
    best_params, best_aic = stop_criteria.auto_sarima_stop_criteria(
        max_p=2, max_d=1, max_q=2,
        max_P=1, max_D=1, max_Q=1
    )
    
    if best_params:
        p, d, q, P, D, Q = best_params
        print(f"最佳SARIMA參數: SARIMA({p},{d},{q})({P},{D},{Q},12)")
        print(f"最佳AIC: {best_aic:.2f}")
        
        # 使用最佳參數進行預測
        model = SARIMAX(data, order=(p, d, q), seasonal_order=(P, D, Q, 12))
        fitted_model = model.fit(disp=False)
        forecast = fitted_model.forecast(steps=12)
        print(f"預測結果: {forecast}")
    else:
        print("無法找到合適的SARIMA參數")


def example_comprehensive_forecast_workflow():
    """
    綜合預測工作流程範例
    """
    print("\n=== 綜合預測工作流程範例 ===")
    
    # 生成數據
    data = generate_sample_data(60, 12)
    
    # 創建評估器
    stop_criteria = create_forecast_stop_criteria(data, seasonal_period=12)
    
    # 步驟1: 檢查是否可以進行預測
    can_forecast, stop_reasons = stop_criteria.comprehensive_check()
    
    if not can_forecast:
        print("❌ 不建議進行預測:")
        for reason in stop_reasons:
            print(f"  - {reason}")
        return
    
    print("✅ 可以進行預測")
    
    # 步驟2: 獲取建議的預測週期
    forecast_period = stop_criteria.get_dynamic_forecast_period()
    print(f"建議預測週期: {forecast_period}")
    
    # 步驟3: 進行SARIMA預測
    best_params, best_aic = stop_criteria.auto_sarima_stop_criteria()
    
    if best_params:
        p, d, q, P, D, Q = best_params
        
        # 擬合模型
        model = SARIMAX(data, order=(p, d, q), seasonal_order=(P, D, Q, 12))
        fitted_model = model.fit(disp=False)
        
        # 生成預測
        forecast = fitted_model.forecast(steps=forecast_period)
        
        print(f"預測完成:")
        print(f"  模型: SARIMA({p},{d},{q})({P},{D},{Q},12)")
        print(f"  AIC: {best_aic:.2f}")
        print(f"  預測值: {forecast}")
        
        # 步驟4: 監控預測質量（如果有實際值）
        # 這裡使用最後12個數據點作為"實際值"來演示
        if len(data) >= 12:
            actual_test = data[-12:]
            predicted_test = fitted_model.forecast(steps=12)
            
            quality_alerts = stop_criteria.monitor_forecast_quality(
                actual_test, predicted_test
            )
            
            if quality_alerts:
                print("⚠️ 預測質量警報:")
                for alert in quality_alerts:
                    print(f"  - {alert}")
            else:
                print("✅ 預測質量良好")
    
    else:
        print("❌ 無法找到合適的SARIMA參數")


def example_visualization():
    """
    視覺化範例 (暫時禁用)
    """
    print("\n=== 視覺化範例 ===")
    print("視覺化功能暫時禁用，需要安裝 matplotlib")
    
    # 生成數據
    data = generate_sample_data(60, 12)
    
    # 創建評估器
    stop_criteria = ForecastStopCriteria(data, seasonal_period=12)
    
    # 檢測到的週期
    detected_periods = stop_criteria.detect_multiple_periods()
    
    if detected_periods:
        print("檢測到的週期:")
        for period_name, period_info in detected_periods.items():
            print(f"  - {period_name}: 強度 {period_info['strength']:.3f}")
    
    print("如需視覺化功能，請安裝 matplotlib: pip install matplotlib")


if __name__ == "__main__":
    print("預測停止條件使用範例")
    print("=" * 50)
    
    # 運行所有範例
    example_basic_usage()
    example_seasonal_analysis()
    example_forecast_quality_monitoring()
    example_sarima_parameter_optimization()
    example_comprehensive_forecast_workflow()
    example_visualization()
    
    print("\n" + "=" * 50)
    print("所有範例執行完成！") 