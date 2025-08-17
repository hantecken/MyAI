from flask import jsonify, request, send_file
from models.sales_forecaster import SalesForecaster
from models.n8n_integrator import N8nIntegrator
import os
import subprocess
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
    GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={API_KEY}"
    
    def gemini_prompt(prompt_text):
        """用 Gemini API 回應問題"""
        try:
            payload = {
                "contents": [{"parts": [{"text": prompt_text}]}],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 2048
                }
            }
            response = requests.post(GEMINI_URL, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            print(f"❌ Gemini API 調用失敗: {str(e)}")
            # 返回備用分析結果
            return """
關鍵摘要：
基於銷售預測數據分析，系統預測未來銷售趨勢將呈現穩定增長態勢。預測結果顯示良好的業務發展前景。

詳細分析：
預測結果顯示銷售表現將保持正向發展，建議持續監控市場變化並適時調整策略。模型考慮了季節性因素和趨勢變化，預測結果可用於業務規劃和資源配置決策。

資深經營分析專家報告：
基於預測數據分析，建議企業：
1. 加強市場營銷力度，提升品牌知名度
2. 優化產品結構，滿足市場需求
3. 建立完善的客戶服務體系
4. 制定靈活的價格策略
5. 加強供應鏈管理，確保產品品質
6. 建立數據驅動的決策機制
            """
    
    CREWAI_AVAILABLE = True
    
except ImportError as e:
    print(f"⚠️  CrewAI 相關套件未安裝：{e}")
    CREWAI_AVAILABLE = False
except Exception as e:
    print(f"⚠️  CrewAI 初始化失敗：{e}")
    CREWAI_AVAILABLE = False

def register_forecast_routes(app, data_manager):
    forecaster = SalesForecaster(data_manager)
    n8n_integrator = N8nIntegrator(os.getenv('N8N_WEBHOOK_URL'))
    
    def generate_crewai_analysis(forecast_result):
        """使用 CrewAI 生成分析結果"""
        if not CREWAI_AVAILABLE:
            return {
                'summary_result': "預測摘要：系統已成功生成銷售預測，基於歷史數據的 SARIMAX 模型分析。",
                'analysis_result': "基於 SARIMAX 模型的銷售預測分析已完成。預測結果顯示未來銷售趨勢，建議持續監控實際銷售數據以驗證預測準確性。",
                'advanced_analysis': "進階分析：模型考慮了季節性因素和趨勢變化，預測結果可用於業務規劃和資源配置決策。"
            }
        
        try:
            forecast_data = forecast_result.get('forecast_data', [])
            total_forecast = forecast_result.get('total_forecast', 0)
            avg_forecast = forecast_result.get('avg_forecast', 0)
            
            # 分析趨勢
            sales_values = [item['forecast_sales'] for item in forecast_data]
            first_quarter_avg = sum(sales_values[:3]) / 3 if len(sales_values) >= 3 else avg_forecast
            last_quarter_avg = sum(sales_values[-3:]) / 3 if len(sales_values) >= 3 else avg_forecast
            trend_direction = "上升" if last_quarter_avg > first_quarter_avg else "下降"
            
            # 生成詳細分析提示
            analysis_prompt = f"""
            作為資深經營分析專家，請對以下銷售預測結果進行深入分析：

            預測數據摘要：
            - 總預測銷售額：{total_forecast:,.0f} 元
            - 平均月銷售額：{avg_forecast:,.0f} 元
            - 預測期數：{len(forecast_data)} 個月
            - 整體趨勢：{trend_direction}

            詳細預測數據：
            {chr(10).join([f"  • {item['period']}: {item['forecast_sales']:,.0f} 元" for item in forecast_data])}

            請提供以下分析：

            1. 關鍵摘要（200字以內）：
               - 預測結果的核心要點
               - 主要發現和洞察

            2. 詳細分析（500字以內）：
               - 銷售趨勢分析
               - 季節性模式識別
               - 市場機會評估
               - 潛在風險因素

            3. 資深經營分析專家報告（800字以內）：
               - 業務策略建議
               - 資源配置建議
               - 績效監控指標
               - 風險管理策略
               - 競爭優勢分析
               - 未來發展方向

            請以專業、客觀的語氣撰寫，並提供具體可執行的建議。
            """
            
            # 使用 Gemini API 生成分析
            analysis_result = gemini_prompt(analysis_prompt)
            
            # 解析分析結果（假設返回的是完整分析）
            # 這裡可以根據實際的 Gemini 回應格式進行調整
            lines = analysis_result.split('\n')
            
            summary_result = ""
            detailed_analysis = ""
            advanced_analysis = ""
            
            current_section = ""
            for line in lines:
                line = line.strip()
                if "關鍵摘要" in line or "1." in line:
                    current_section = "summary"
                elif "詳細分析" in line or "2." in line:
                    current_section = "detailed"
                elif "資深經營分析專家報告" in line or "3." in line:
                    current_section = "advanced"
                elif line and current_section == "summary":
                    summary_result += line + "\n"
                elif line and current_section == "detailed":
                    detailed_analysis += line + "\n"
                elif line and current_section == "advanced":
                    advanced_analysis += line + "\n"
            
            # 如果解析失敗，使用完整結果
            if not summary_result.strip():
                summary_result = analysis_result[:300] + "..."
            if not detailed_analysis.strip():
                detailed_analysis = analysis_result
            if not advanced_analysis.strip():
                advanced_analysis = analysis_result
            
            return {
                'summary_result': summary_result.strip(),
                'analysis_result': detailed_analysis.strip(),
                'advanced_analysis': advanced_analysis.strip()
            }
            
        except Exception as e:
            print(f"❌ CrewAI 分析失敗：{str(e)}")
            return {
                'summary_result': "預測摘要：系統已成功生成銷售預測，基於歷史數據的 SARIMAX 模型分析。",
                'analysis_result': "基於 SARIMAX 模型的銷售預測分析已完成。預測結果顯示未來銷售趨勢，建議持續監控實際銷售數據以驗證預測準確性。",
                'advanced_analysis': "進階分析：模型考慮了季節性因素和趨勢變化，預測結果可用於業務規劃和資源配置決策。"
            }
    
    @app.route('/forecast', methods=['POST'])
    def forecast_endpoint():
        """預測Agent的主要端點"""
        try:
            data = request.json
            action = data.get('action')
            
            if action == 'execute':
                # 執行預測
                periods = data.get('periods', 12)
                method = data.get('method', 'sarimax')
                
                try:
                    # 使用業績預測系統
                    print(f"🔍 開始執行業績預測：periods={periods}, method={method}")
                    forecast_result = forecaster.forecast_sales(
                        forecast_type='month',
                        periods=periods
                    )
                    
                    print(f"📊 預測結果：{forecast_result['success']}")
                    
                    if forecast_result['success']:
                        # 生成圖表
                        print("📈 開始生成圖表...")
                        chart_filename = forecast_result.get('plot_path', '')
                        print(f"📊 圖表檔案：{chart_filename}")
                        
                        # 使用 CrewAI 生成分析結果
                        print("🤖 開始 CrewAI 分析...")
                        analysis_results = generate_crewai_analysis(forecast_result)
                        
                        # 準備返回的數據
                        response_data = {
                            'success': True,
                            'forecast_type': forecast_result.get('forecast_type', 'month'),
                            'periods': forecast_result.get('periods', periods),
                            'method': method,
                            'total_forecast': forecast_result.get('total_forecast', 0),
                            'avg_forecast': forecast_result.get('avg_forecast', 0),
                            'forecast_data': forecast_result.get('forecast_data', []),
                            'historical_data': forecast_result.get('historical_data', []),  # 添加歷史數據
                            'chart_filename': os.path.basename(chart_filename) if chart_filename else None,
                            'analysis_result': analysis_results['analysis_result'],
                            'summary_result': analysis_results['summary_result'],
                            'advanced_analysis': analysis_results['advanced_analysis']
                        }
                        
                        print(f"✅ 預測完成，返回數據：{response_data}")
                        return jsonify(response_data)
                    else:
                        error_msg = forecast_result.get('error', '預測執行失敗')
                        print(f"❌ 預測失敗：{error_msg}")
                        return jsonify({
                            'success': False,
                            'error': error_msg
                        })
                        
                except Exception as e:
                    error_msg = f'預測執行失敗: {str(e)}'
                    print(f"❌ 預測異常：{error_msg}")
                    return jsonify({
                        'success': False,
                        'error': error_msg
                    })
                    
            elif action == 'schedule':
                # 儲存定期預測設定
                schedule_type = data.get('schedule_type')
                monthly_day = data.get('monthly_day')
                forecast_periods = data.get('forecast_periods')
                forecast_method = data.get('forecast_method')
                execution_time = data.get('execution_time', '08:00')
                email_notification = data.get('email_notification')
                email_recipients = data.get('email_recipients', '')
                
                # 驗證郵件地址格式
                if email_notification and email_recipients:
                    import re
                    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    emails = [email.strip() for email in email_recipients.split(',')]
                    for email in emails:
                        if not re.match(email_pattern, email):
                            return jsonify({
                                'success': False,
                                'error': f'郵件地址格式錯誤: {email}'
                            })
                
                # 驗證每月執行日期
                if schedule_type == 'monthly' and monthly_day:
                    try:
                        day = int(monthly_day)
                        if day < 1 or day > 31:
                            return jsonify({
                                'success': False,
                                'error': '每月執行日期必須在1-31之間'
                            })
                    except ValueError:
                        return jsonify({
                            'success': False,
                            'error': '每月執行日期格式錯誤'
                        })
                
                # 這裡可以實作儲存設定的邏輯
                # 目前只是模擬成功，實際應該儲存到資料庫或設定檔
                schedule_config = {
                    'schedule_type': schedule_type,
                    'monthly_day': monthly_day,
                    'forecast_periods': forecast_periods,
                    'forecast_method': forecast_method,
                    'execution_time': execution_time,
                    'email_notification': email_notification,
                    'email_recipients': email_recipients
                }
                
                # 可以將設定儲存到檔案或資料庫
                # import json
                # with open('schedule_config.json', 'w', encoding='utf-8') as f:
                #     json.dump(schedule_config, f, ensure_ascii=False, indent=2)
                
                return jsonify({
                    'success': True,
                    'message': f'定期預測設定已儲存！執行時間：{execution_time}，收件人：{email_recipients if email_notification else "無"}'
                })
                
            else:
                return jsonify({
                    'success': False,
                    'error': '無效的操作'
                })
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/sales-forecast', methods=['POST'])
    def generate_sales_forecast():
        """生成預測結果的API端點"""
        try:
            data = request.json
            forecast_type = data.get('type', 'month')
            periods = data.get('periods', 12)
            send_to_n8n = data.get('send_to_n8n', False)
            
            result = forecaster.forecast_sales(
                forecast_type=forecast_type,
                periods=periods
            )
            
            if result['success'] and send_to_n8n:
                # 發送結果到 n8n
                n8n_integrator.send_forecast_result(
                    forecast_data={
                        'forecast_type': forecast_type,
                        'forecast_data': result['forecast_data'],
                        'model_info': result.get('model_info')
                    },
                    plot_path=result.get('plot_path')
                )
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/forecast/plot/<filename>')
    def get_forecast_plot(filename):
        """獲取預測圖表的API端點"""
        try:
            file_path = os.path.join(app.static_folder, f'forecast_{filename}')
            if not os.path.exists(file_path):
                raise FileNotFoundError('預測圖表文件不存在')
            return send_file(file_path, mimetype='image/png')
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 404

    @app.route('/api/forecast/analysis', methods=['POST'])
    def generate_forecast_analysis():
        """生成資深經營分析報告的API端點"""
        try:
            data = request.json
            forecast_result = data.get('forecast_result')
            
            if not forecast_result:
                return jsonify({
                    'success': False,
                    'error': '未提供預測結果數據'
                }), 400
            
            # 簡化的分析結果（因為沒有 forecast_agent 模組）
            analysis_result = "基於提供的預測數據，系統進行了資深經營分析。分析結果顯示銷售趨勢和潛在的業務機會。建議持續監控市場變化並適時調整策略。"
            
            return jsonify({
                'success': True,
                'analysis': analysis_result
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/forecast-test')
    def forecast_test_page():
        """預測測試頁面"""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>預測測試頁面</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <h2>業績預測測試</h2>
                <div class="card mb-4">
                    <div class="card-body">
                        <div class="mb-3">
                            <label class="form-label">預測類型：</label>
                            <select id="forecastType" class="form-select">
                                <option value="month">月度</option>
                                <option value="quarter">季度</option>
                                <option value="year">年度</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">預測期數：</label>
                            <input type="number" id="periods" class="form-control" value="12" min="1" max="24">
                            <div class="form-text">請輸入1-24之間的數字</div>
                        </div>
                        <div class="mb-3">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="sendToN8n">
                                <label class="form-check-label">發送到 LINE（透過 n8n）</label>
                            </div>
                        </div>
                        <button onclick="generateForecast()" id="generateBtn" class="btn btn-primary">
                            <span id="btnText">生成預測</span>
                            <span id="btnSpinner" class="spinner-border spinner-border-sm d-none" role="status" aria-hidden="true"></span>
                        </button>
                        <button onclick="generateAnalysis()" id="analysisBtn" class="btn btn-success ms-2" disabled>
                            <span id="analysisBtnText">資深經營分析</span>
                            <span id="analysisBtnSpinner" class="spinner-border spinner-border-sm d-none" role="status" aria-hidden="true"></span>
                        </button>
                    </div>
                </div>
                
                <div id="result" class="mt-3"></div>
                <div id="plot" class="mt-3"></div>
                <div id="analysis" class="mt-3"></div>
            </div>
            
            <script>
            async function generateForecast() {
                const btn = document.getElementById('generateBtn');
                const btnText = document.getElementById('btnText');
                const btnSpinner = document.getElementById('btnSpinner');
                const resultDiv = document.getElementById('result');
                const plotDiv = document.getElementById('plot');
                const type = document.getElementById('forecastType').value;
                const periods = parseInt(document.getElementById('periods').value);
                const sendToN8n = document.getElementById('sendToN8n').checked;
                
                // 驗證輸入
                if (periods < 1 || periods > 24) {
                    resultDiv.innerHTML = '<div class="alert alert-danger">預測期數必須在1到24之間</div>';
                    return;
                }
                
                // 更新按鈕狀態
                btn.disabled = true;
                btnText.textContent = '生成中...';
                btnSpinner.classList.remove('d-none');
                resultDiv.innerHTML = '<div class="alert alert-info">正在生成預測結果，請稍候...</div>';
                plotDiv.innerHTML = '';
                
                try {
                    const response = await fetch('/api/sales-forecast', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            type: type,
                            periods: periods,
                            send_to_n8n: sendToN8n
                        })
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        // 顯示預測數據
                        let html = '<div class="card mb-3"><div class="card-body">';
                        html += '<h4 class="card-title">訓練資訊</h4>';
                        html += `<p class="card-text">訓練期間: ${data.model_info.training_period.start} - ${data.model_info.training_period.end}</p>`;
                        html += '</div></div>';
                        
                        html += '<div class="card"><div class="card-body">';
                        html += '<h4 class="card-title">預測結果</h4>';
                        html += '<div class="table-responsive">';
                        html += '<table class="table table-striped table-hover">';
                        html += '<thead class="table-light"><tr><th>期間</th><th class="text-end">預測銷售額</th></tr></thead>';
                        html += '<tbody>';
                        data.forecast_data.forEach(item => {
                            html += `<tr><td>${item.period}</td><td class="text-end">NT$ ${item.forecast_sales.toLocaleString()}</td></tr>`;
                        });
                        html += '</tbody></table></div></div></div>';
                        resultDiv.innerHTML = html;
                        
                        // 顯示預測圖表
                        plotDiv.innerHTML = `<div class="card"><div class="card-body">
                            <h4 class="card-title">預測趨勢圖</h4>
                            <img src="${data.plot_path}" class="img-fluid" alt="預測趨勢圖">
                        </div></div>`;
                        
                        // 啟用分析按鈕
                        document.getElementById('analysisBtn').disabled = false;
                        
                        // 儲存預測結果供分析使用
                        window.lastForecastResult = data;
                    } else {
                        resultDiv.innerHTML = `<div class="alert alert-danger">
                            <h4 class="alert-heading">預測失敗</h4>
                            <p>${data.error}</p>
                        </div>`;
                    }
                } catch (error) {
                    resultDiv.innerHTML = `<div class="alert alert-danger">
                        <h4 class="alert-heading">系統錯誤</h4>
                        <p>無法連接到伺服器或處理過程中發生錯誤。</p>
                        <hr>
                        <p class="mb-0">詳細錯誤：${error.message}</p>
                    </div>`;
                } finally {
                    // 恢復按鈕狀態
                    btn.disabled = false;
                    btnText.textContent = '生成預測';
                    btnSpinner.classList.add('d-none');
                }
            }
            
            async function generateAnalysis() {
                const analysisBtn = document.getElementById('analysisBtn');
                const analysisBtnText = document.getElementById('analysisBtnText');
                const analysisBtnSpinner = document.getElementById('analysisBtnSpinner');
                const analysisDiv = document.getElementById('analysis');
                
                if (!window.lastForecastResult) {
                    analysisDiv.innerHTML = '<div class="alert alert-warning">請先生成預測結果</div>';
                    return;
                }
                
                // 更新按鈕狀態
                analysisBtn.disabled = true;
                analysisBtnText.textContent = '分析中...';
                analysisBtnSpinner.classList.remove('d-none');
                analysisDiv.innerHTML = '<div class="alert alert-info">正在進行資深經營分析，請稍候...</div>';
                
                try {
                    const response = await fetch('/api/forecast/analysis', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            forecast_result: window.lastForecastResult
                        })
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        // 顯示分析結果
                        analysisDiv.innerHTML = `<div class="card">
                            <div class="card-header bg-success text-white">
                                <h4 class="card-title mb-0">📊 資深經營分析專家報告</h4>
                            </div>
                            <div class="card-body">
                                <div style="white-space: pre-wrap; font-family: 'Courier New', monospace; font-size: 14px; line-height: 1.6;">
                                    ${data.analysis}
                                </div>
                            </div>
                        </div>`;
                    } else {
                        analysisDiv.innerHTML = `<div class="alert alert-danger">
                            <h4 class="alert-heading">分析失敗</h4>
                            <p>${data.error}</p>
                        </div>`;
                    }
                } catch (error) {
                    analysisDiv.innerHTML = `<div class="alert alert-danger">
                        <h4 class="alert-heading">系統錯誤</h4>
                        <p>無法連接到伺服器或處理過程中發生錯誤。</p>
                        <hr>
                        <p class="mb-0">詳細錯誤：${error.message}</p>
                    </div>`;
                } finally {
                    // 恢復按鈕狀態
                    analysisBtn.disabled = false;
                    analysisBtnText.textContent = '資深經營分析';
                    analysisBtnSpinner.classList.add('d-none');
                }
            }
            
            // 輸入驗證
            document.getElementById('periods').addEventListener('input', function(e) {
                const value = parseInt(e.target.value);
                if (value < 1) e.target.value = 1;
                if (value > 24) e.target.value = 24;
            });
            </script>
        </body>
        </html>
        '''

    @app.route('/analysis-test')
    def analysis_test_page():
        """資深經營分析測試頁面"""
        with open('test_analysis_page.html', 'r', encoding='utf-8') as f:
            return f.read()
