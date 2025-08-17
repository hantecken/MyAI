# 統一預測系統路由
# 整合業績預測和分析結果預測功能

from flask import Blueprint, request, jsonify, render_template, send_file, redirect
from models.unified_forecaster import UnifiedForecaster
from datetime import datetime
import os

def register_unified_forecast_routes(app, data_manager):
    """註冊統一預測路由"""
    
    # 創建統一預測器實例
    unified_forecaster = UnifiedForecaster(data_manager)
    
    @app.route('/unified-forecast', methods=['GET'])
    def unified_forecast_page():
        """統一預測頁面"""
        return render_template('unified_forecast.html')
    
    @app.route('/unified-forecast-test')
    def unified_forecast_test_page():
        """統一預測測試頁面 - 重定向到主頁面"""
        return redirect('/unified-forecast')
    
    @app.route('/api/unified-forecast', methods=['POST'])
    def generate_unified_forecast():
        """生成統一預測結果的API端點"""
        try:
            data = request.json
            forecast_type = data.get('type', 'month')
            periods = data.get('periods', 12)
            enable_ai_analysis = data.get('enable_ai_analysis', True)
            
            print(f"🚀 開始統一預測：type={forecast_type}, periods={periods}, ai_analysis={enable_ai_analysis}")
            
            # 執行統一預測
            result = unified_forecaster.generate_unified_forecast(
                forecast_type=forecast_type,
                periods=periods,
                enable_ai_analysis=enable_ai_analysis
            )
            
            if result['success']:
                print("✅ 統一預測成功")
                print(f"📊 預測數據點數：{len(result['forecast_data'])}")
                print(f"💰 總預測銷售額：{result['total_forecast']:,.0f} 元")
                print(f"📈 平均月銷售額：{result['avg_forecast']:,.0f} 元")
                
                if result.get('chart_filename'):
                    print(f"📊 圖表檔案：{result['chart_filename']}")
                
                if result.get('ai_analysis', {}).get('success'):
                    print("🤖 AI 分析成功")
                else:
                    print("⚠️ AI 分析未執行或失敗")
            else:
                print(f"❌ 統一預測失敗：{result['error']}")
            
            return jsonify(result)
            
        except Exception as e:
            print(f"❌ 統一預測API錯誤：{str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    @app.route('/api/forecast-agent', methods=['POST'])
    def forecast_agent_endpoint():
        """預測Agent端點 - 提供完整的預測和分析功能"""
        try:
            data = request.json
            forecast_type = data.get('type', 'month')
            periods = data.get('periods', 12)
            
            print(f"🤖 預測Agent執行：type={forecast_type}, periods={periods}")
            
            # 執行統一預測（包含AI分析）
            result = unified_forecaster.generate_unified_forecast(
                forecast_type=forecast_type,
                periods=periods,
                enable_ai_analysis=True  # 預測Agent預設啟用AI分析
            )
            
            if result['success']:
                # 格式化為預測Agent的返回格式
                agent_result = {
                    'success': True,
                    'execution_time': datetime.now().strftime('%Y/%m/%d %p%I:%M:%S'),
                    'forecast_type': forecast_type,
                    'forecast_periods': f"{periods} 個月",
                    'total_forecast_sales': f"{result['total_forecast']:,.0f} 元",
                    'avg_sales': f"{result['avg_forecast']:,.0f} 元",
                    'status': '完成',
                    'forecast_data': result['forecast_data'],
                    'historical_data': result.get('historical_data', {}).get('data', []),  # 添加歷史數據
                    'historical_dates': result.get('historical_data', {}).get('dates', []),  # 添加歷史日期
                    'chart_filename': result.get('chart_filename'),
                    'ai_analysis': result.get('ai_analysis', {}),
                    'model_info': result.get('model_info', {}),
                    'timestamp': datetime.now().isoformat()
                }
                
                print("✅ 預測Agent執行成功")
                return jsonify(agent_result)
            else:
                print(f"❌ 預測Agent執行失敗：{result['error']}")
                return jsonify({
                    'success': False,
                    'error': result['error'],
                    'timestamp': datetime.now().isoformat()
                }), 500
                
        except Exception as e:
            print(f"❌ 預測Agent錯誤：{str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    @app.route('/api/forecast-chart/<filename>')
    def get_forecast_chart(filename):
        """獲取預測圖表檔案"""
        try:
            chart_path = os.path.join('static', filename)
            if os.path.exists(chart_path):
                return send_file(chart_path, mimetype='image/png')
            else:
                return jsonify({
                    'success': False,
                    'error': '圖表檔案不存在'
                }), 404
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
