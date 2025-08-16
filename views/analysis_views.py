# views/analysis_views.py
# 分析視圖 - 負責處理 HTTP 請求和響應

from flask import Blueprint, render_template, request, jsonify, send_file
import pandas as pd
from datetime import datetime, timedelta
import os
import tempfile

# 創建藍圖
analysis_bp = Blueprint('analysis', __name__)

def init_analysis_views(app, analysis_controller, data_manager):
    """
    初始化分析視圖
    """
    
    @app.route('/')
    def index():
        """主頁面"""
        return render_template('index.html')

    @app.route('/analyze', methods=['POST'])
    def analyze():
        """分析查詢端點"""
        try:
            data = request.get_json()
            query = data.get('query', '')
            
            # 使用控制器處理查詢
            result = analysis_controller.analyze_query(query)
            
            if result['success']:
                # 保存當前分析結果供 drill down 使用
                result['currentAnalysisResult'] = {
                    'current_start': result['current_start'],
                    'current_end': result['current_end'],
                    'last_start': result['last_start'],
                    'last_end': result['last_end'],
                    'current_dimension': result['current_dimension']
                }
                return jsonify(result)
            else:
                return jsonify({'error': result['error']}), 400
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/drill-down', methods=['POST'])
    def drill_down():
        """Drill Down 分析端點"""
        try:
            data = request.get_json()
            
            result = analysis_controller.drill_down_analysis(
                data['current_start'],
                data['current_end'],
                data['last_start'],
                data['last_end'],
                data['primary_dimension'],
                data['primary_value'],
                data['drill_dimension']
            )
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify({'error': result['error']}), 400
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/db/tables', methods=['GET'])
    def get_tables():
        """獲取所有資料表"""
        try:
            tables = data_manager.get_all_tables()
            return jsonify({'tables': tables})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/db/schema/<table_name>', methods=['GET'])
    def get_table_schema(table_name):
        """獲取資料表結構"""
        try:
            schema = data_manager.get_table_schema(table_name)
            return jsonify({
                'table_name': table_name,
                'schema': schema.to_dict('records')
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/db/data/<table_name>', methods=['GET'])
    def get_table_data(table_name):
        """獲取資料表數據"""
        try:
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 10))
            
            result = data_manager.get_table_data(table_name, page, limit)
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/db/execute', methods=['POST'])
    def execute_sql():
        """執行自定義 SQL 查詢"""
        try:
            data = request.get_json()
            sql_query = data.get('sql', '')
            is_natural_language = data.get('is_natural_language', False)
            
            if not sql_query:
                return jsonify({'error': '查詢不能為空'}), 400
            
            # 如果是自然語言查詢，先轉換為SQL
            if is_natural_language:
                try:
                    generated_sql = analysis_controller.natural_language_to_sql(sql_query, sql_query)
                    if generated_sql:
                        sql_query = generated_sql
                        result = data_manager.execute_custom_sql(sql_query)
                        if result['success']:
                            result['generated_sql'] = generated_sql
                            return jsonify(result)
                        else:
                            return jsonify({'error': result['error']}), 400
                    else:
                        return jsonify({'error': '無法將自然語言轉換為SQL查詢'}), 400
                except Exception as e:
                    return jsonify({'error': f'自然語言轉換失敗: {str(e)}'}), 400
            else:
                # 直接執行SQL查詢
                result = data_manager.execute_custom_sql(sql_query)
                
                if result['success']:
                    return jsonify(result)
                else:
                    return jsonify({'error': result['error']}), 400
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/db/export/<table_name>', methods=['GET'])
    def export_table(table_name):
        """匯出資料表數據"""
        try:
            # 獲取所有數據
            result = data_manager.execute_custom_sql(f'SELECT * FROM {table_name}')
            
            if result['success']:
                # 轉換為 CSV 格式
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # 寫入標題行
                if result['data']:
                    writer.writerow(result['data'][0].keys())
                    # 寫入數據行
                    for row in result['data']:
                        writer.writerow(row.values())
                
                from flask import Response
                return Response(
                    output.getvalue(),
                    mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={table_name}.csv'}
                )
            else:
                return jsonify({'error': result['error']}), 400
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/chat', methods=['POST'])
    def chat():
        """AI 聊天端點"""
        try:
            data = request.get_json()
            message = data.get('message', '')
            analysis_context = data.get('analysis_context')
            chat_history = data.get('chat_history', [])
            
            # 使用控制器處理聊天
            result = analysis_controller.chat_with_ai(message, analysis_context, chat_history)
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/generate-report', methods=['POST'])
    def generate_report():
        """生成專業報告端點"""
        try:
            data = request.get_json()
            report_type = data.get('report_type', 'general')
            analysis_context = data.get('analysis_context')
            chat_context = data.get('chat_context', [])
            
            # 使用控制器生成報告
            result = analysis_controller.generate_professional_report(
                analysis_context, report_type, chat_context
            )
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/generate-forecast', methods=['POST'])
    def generate_forecast():
        """生成預測端點"""
        try:
            data = request.get_json()
            forecast_type = data.get('forecast_type', 'month')
            periods = data.get('periods', 12)
            dimension = data.get('dimension', 'all')
            value = data.get('value')
            model_type = data.get('model', 'arima')  # 新增模型選擇參數
            
            # 根據模型類型選擇預測方法
            if model_type == 'ets':
                result = analysis_controller.generate_ets_forecast(
                    forecast_type, periods, dimension, value
                )
            else:  # 預設使用統一預測系統
                result = analysis_controller.generate_unified_forecast(
                    forecast_type, periods, dimension, value
                )
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/dimension-list')
    def get_dimension_list():
        """取得產品或客戶清單供預測下拉選單使用"""
        dim = request.args.get('dimension')
        if dim == 'product':
            df = data_manager.execute_query('SELECT product_id, product_name FROM dim_product')
            result = [{'id': int(row['product_id']), 'name': row['product_name']} for _, row in df.iterrows()]
        elif dim == 'customer':
            df = data_manager.execute_query('SELECT customer_id, customer_name FROM dim_customer')
            result = [{'id': int(row['customer_id']), 'name': row['customer_name']} for _, row in df.iterrows()]
        else:
            result = []
        return jsonify(result)

    @app.route('/api/n8n/line-notification', methods=['POST'])
    def n8n_line_notification():
        """
        n8n LINE 通知 API 端點
        接收 n8n 的 POST 請求，返回適合 LINE 通知的數據格式
        """
        try:
            # 獲取請求數據
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': '缺少請求數據'
                }), 400
            
            # 解析參數
            query_type = data.get('query_type', 'summary')
            custom_query = data.get('custom_query')
            time_range = data.get('time_range')
            
            # 驗證必要參數
            if query_type == 'custom' and not custom_query:
                return jsonify({
                    'success': False,
                    'error': '自定義查詢類型需要提供 custom_query 參數'
                }), 400
            
            # 生成 LINE 通知數據
            result = analysis_controller.generate_line_notification_data(
                query_type=query_type,
                custom_query=custom_query,
                time_range=time_range
            )
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': result['message'],
                    'data': result.get('data', {}),
                    'timestamp': datetime.now().isoformat(),
                    'query_type': query_type
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result['error']
                }), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'API 執行失敗: {str(e)}'
            }), 500

    @app.route('/api/n8n/line-notification/schedule', methods=['POST'])
    def n8n_scheduled_line_notification():
        """
        n8n 定時 LINE 通知 API 端點
        用於定時任務，自動生成並返回 LINE 通知數據
        """
        try:
            # 獲取請求數據
            data = request.get_json() or {}
            
            # 解析參數
            schedule_type = data.get('schedule_type', 'daily')  # daily, weekly, monthly
            report_type = data.get('report_type', 'summary')    # summary, product, staff, customer, region
            custom_message = data.get('custom_message', '')
            
            # 根據排程類型設定時間範圍
            today = datetime(2025, 7, 10)  # 使用固定日期進行演示
            
            if schedule_type == 'daily':
                # 今日 vs 昨日
                current_start = today.strftime('%Y-%m-%d')
                current_end = today.strftime('%Y-%m-%d')
                last_start = (today - timedelta(days=1)).strftime('%Y-%m-%d')
                last_end = (today - timedelta(days=1)).strftime('%Y-%m-%d')
                period_text = "今日 vs 昨日"
            elif schedule_type == 'weekly':
                # 本週 vs 上週
                current_start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
                current_end = today.strftime('%Y-%m-%d')
                last_start = (today - timedelta(days=today.weekday() + 7)).strftime('%Y-%m-%d')
                last_end = (today - timedelta(days=today.weekday() + 1)).strftime('%Y-%m-%d')
                period_text = "本週 vs 上週"
            elif schedule_type == 'monthly':
                # 本月 vs 上月
                current_start = today.replace(day=1).strftime('%Y-%m-%d')
                current_end = today.strftime('%Y-%m-%d')
                last_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1).strftime('%Y-%m-%d')
                last_end = (today.replace(day=1) - timedelta(days=1)).strftime('%Y-%m-%d')
                period_text = "本月 vs 上月"
            else:
                return jsonify({
                    'success': False,
                    'error': '無效的排程類型'
                }), 400
            
            time_range = {
                'current_start': current_start,
                'current_end': current_end,
                'last_start': last_start,
                'last_end': last_end
            }
            
            # 生成 LINE 通知數據
            result = analysis_controller.generate_line_notification_data(
                query_type=report_type,
                time_range=time_range
            )
            
            if result['success']:
                # 添加自定義訊息
                if custom_message:
                    result['message'] = f"{custom_message}\n\n{result['message']}"
                
                # 添加排程資訊
                result['message'] = f"📅 {period_text} 自動報告\n{result['message']}"
                
                return jsonify({
                    'success': True,
                    'message': result['message'],
                    'data': result.get('data', {}),
                    'timestamp': datetime.now().isoformat(),
                    'schedule_type': schedule_type,
                    'report_type': report_type,
                    'period_text': period_text
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result['error']
                }), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'定時通知 API 執行失敗: {str(e)}'
            }), 500

    @app.route('/api/n8n/line-notification/alert', methods=['POST'])
    def n8n_alert_line_notification():
        """
        n8n 警報 LINE 通知 API 端點
        用於異常情況的即時通知
        """
        try:
            # 獲取請求數據
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': '缺少請求數據'
                }), 400
            
            # 解析參數
            alert_type = data.get('alert_type', 'performance')  # performance, threshold, anomaly
            threshold_value = data.get('threshold_value', 0)
            alert_message = data.get('alert_message', '')
            time_range = data.get('time_range')
            
            # 生成警報通知
            if alert_type == 'performance':
                # 業績警報
                result = analysis_controller.generate_line_notification_data(
                    query_type='summary',
                    time_range=time_range
                )
                
                if result['success']:
                    # 檢查是否超過閾值
                    data_info = result.get('data', {})
                    current_sales = data_info.get('current_sales', 0)
                    percentage_diff = data_info.get('percentage_diff', 0)
                    
                    if percentage_diff < threshold_value:
                        alert_emoji = "🚨"
                        alert_status = "業績下滑警報"
                    else:
                        alert_emoji = "✅"
                        alert_status = "業績正常"
                    
                    # 組合警報訊息
                    alert_msg = f"{alert_emoji} {alert_status}\n"
                    alert_msg += f"📊 當前業績變化: {percentage_diff:+.1f}%\n"
                    alert_msg += f"🎯 警報閾值: {threshold_value:.1f}%\n\n"
                    alert_msg += result['message']
                    
                    if alert_message:
                        alert_msg = f"{alert_message}\n\n{alert_msg}"
                    
                    return jsonify({
                        'success': True,
                        'message': alert_msg,
                        'data': result.get('data', {}),
                        'alert_type': alert_type,
                        'threshold_value': threshold_value,
                        'current_percentage': percentage_diff,
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': result['error']
                    }), 400
                    
            elif alert_type == 'threshold':
                # 閾值警報
                result = analysis_controller.generate_line_notification_data(
                    query_type='summary',
                    time_range=time_range
                )
                
                if result['success']:
                    data_info = result.get('data', {})
                    current_sales = data_info.get('current_sales', 0)
                    
                    if current_sales < threshold_value:
                        alert_emoji = "⚠️"
                        alert_status = "銷售額低於閾值"
                    else:
                        alert_emoji = "✅"
                        alert_status = "銷售額達標"
                    
                    alert_msg = f"{alert_emoji} {alert_status}\n"
                    alert_msg += f"💰 當前銷售額: {current_sales:,.0f} 元\n"
                    alert_msg += f"🎯 目標閾值: {threshold_value:,.0f} 元\n\n"
                    alert_msg += result['message']
                    
                    if alert_message:
                        alert_msg = f"{alert_message}\n\n{alert_msg}"
                    
                    return jsonify({
                        'success': True,
                        'message': alert_msg,
                        'data': result.get('data', {}),
                        'alert_type': alert_type,
                        'threshold_value': threshold_value,
                        'current_sales': current_sales,
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': result['error']
                    }), 400
                    
            else:
                return jsonify({
                    'success': False,
                    'error': '無效的警報類型'
                }), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'警報通知 API 執行失敗: {str(e)}'
            }), 500

    @app.route('/api/voice/summary', methods=['POST'])
    def generate_voice_summary():
        """
        生成語音總結端點
        播放內容為主要貢獻分析、其他維度參考分析
        播放語音為國語新聞播放女生
        """
        try:
            data = request.get_json()
            summary_text = data.get('summary_text', '')
            voice_type = data.get('voice_type', 'mandarin_female')
            
            if not summary_text:
                return jsonify({
                    'success': False,
                    'error': '缺少分析總結文字'
                }), 400
            
            # 使用控制器生成語音總結
            result = analysis_controller.generate_voice_summary(summary_text, voice_type)
            
            if result['success']:
                # 如果成功生成語音文件，返回文件路徑和內容
                return jsonify({
                    'success': True,
                    'voice_content': result['voice_content'],
                    'audio_file_path': result['audio_file_path'],
                    'main_contribution': result['main_contribution'],
                    'other_dimension': result['other_dimension'],
                    'message': '語音總結生成成功'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result['error']
                }), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'語音總結生成失敗: {str(e)}'
            }), 500

    @app.route('/api/voice/status', methods=['GET'])
    def get_voice_status():
        """
        獲取語音總結功能狀態端點
        """
        try:
            # 使用控制器獲取語音功能狀態
            result = analysis_controller.get_voice_summary_status()
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'獲取語音狀態失敗: {str(e)}'
            }), 500

    @app.route('/api/voice/audio/<filename>', methods=['GET'])
    def get_voice_audio(filename):
        """
        獲取語音音頻文件端點
        """
        try:
            # 構建音頻文件路徑
            temp_dir = os.path.join(tempfile.gettempdir(), 'voice_summary')
            audio_file_path = os.path.join(temp_dir, filename)
            
            # 檢查文件是否存在
            if not os.path.exists(audio_file_path):
                return jsonify({
                    'success': False,
                    'error': '音頻文件不存在'
                }), 404
            
            # 根據文件擴展名設定正確的 MIME 類型
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext == '.mp3':
                mimetype = 'audio/mpeg'
            elif file_ext == '.wav':
                mimetype = 'audio/wav'
            elif file_ext == '.ogg':
                mimetype = 'audio/ogg'
            else:
                mimetype = 'audio/mpeg'  # 預設
            
            print(f"提供音頻文件: {audio_file_path}")
            print(f"文件大小: {os.path.getsize(audio_file_path)} 字節")
            print(f"MIME 類型: {mimetype}")
            
            # 返回音頻文件
            return send_file(
                audio_file_path,
                mimetype=mimetype,
                as_attachment=False,
                download_name=filename
            )
            
        except Exception as e:
            print(f"音頻文件提供失敗: {e}")
            return jsonify({
                'success': False,
                'error': f'獲取音頻文件失敗: {str(e)}'
            }), 500

    @app.route('/audio-test')
    def audio_test_page():
        """
        音頻測試頁面
        """
        return render_template('audio_test.html')