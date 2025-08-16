# 統一預測系統路由
# 整合業績預測和分析結果預測功能

from flask import Blueprint, request, jsonify, render_template, send_file
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
                    'chart_filename': result.get('chart_filename'),
                    'ai_analysis': result.get('ai_analysis', {}),
                    'model_info': result.get('model_info', {}),
                    'timestamp': datetime.now().isoformat()
                }
                
                print("✅ 預測Agent執行成功")
                return jsonify(agent_result)
            else:
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
    
    @app.route('/api/unified-forecast/chart/<filename>')
    def get_unified_forecast_chart(filename):
        """獲取統一預測圖表的API端點"""
        try:
            file_path = os.path.join(app.static_folder, filename)
            if not os.path.exists(file_path):
                raise FileNotFoundError('統一預測圖表文件不存在')
            return send_file(file_path, mimetype='image/png')
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 404
    
    @app.route('/forecast-agent-test')
    def forecast_agent_test_page():
        """預測Agent測試頁面"""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>預測Agent測試</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <div class="row">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header bg-primary text-white">
                                <h3 class="mb-0">
                                    <i class="fas fa-robot"></i> 預測Agent
                                </h3>
                                <p class="mb-0">AI驅動的銷售預測分析系統</p>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="card mb-3">
                                            <div class="card-header bg-warning text-dark">
                                                <h5 class="mb-0">
                                                    <i class="fas fa-bolt"></i> 立即執行預測
                                                </h5>
                                            </div>
                                            <div class="card-body">
                                                <p>立即執行銷售預測分析，獲取最新的預測結果和圖表。</p>
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
                                                </div>
                                                <button onclick="executeForecast()" id="executeBtn" class="btn btn-warning btn-lg">
                                                    <span id="executeBtnText">
                                                        <i class="fas fa-play"></i> 立即執行
                                                    </span>
                                                    <span id="executeBtnSpinner" class="spinner-border spinner-border-sm d-none" role="status" aria-hidden="true"></span>
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="card mb-3">
                                            <div class="card-header bg-info text-white">
                                                <h5 class="mb-0">
                                                    <i class="fas fa-calendar-alt"></i> 定期預測設定
                                                </h5>
                                            </div>
                                            <div class="card-body">
                                                <p>設定定期自動執行預測，每月自動生成預測報告。</p>
                                                <button class="btn btn-info btn-lg">
                                                    <i class="fas fa-cog"></i> 設定排程
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div id="forecastResults" class="mt-4"></div>
                <div id="forecastChart" class="mt-4"></div>
                <div id="aiAnalysis" class="mt-4"></div>
                <div id="historicalRecords" class="mt-4"></div>
            </div>
            
            <script>
            async function executeForecast() {
                const btn = document.getElementById('executeBtn');
                const btnText = document.getElementById('executeBtnText');
                const btnSpinner = document.getElementById('executeBtnSpinner');
                const resultsDiv = document.getElementById('forecastResults');
                const chartDiv = document.getElementById('forecastChart');
                const analysisDiv = document.getElementById('aiAnalysis');
                const recordsDiv = document.getElementById('historicalRecords');
                
                const type = document.getElementById('forecastType').value;
                const periods = parseInt(document.getElementById('periods').value);
                
                // 驗證輸入
                if (periods < 1 || periods > 24) {
                    resultsDiv.innerHTML = '<div class="alert alert-danger">預測期數必須在1到24之間</div>';
                    return;
                }
                
                // 更新按鈕狀態
                btn.disabled = true;
                btnText.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 執行中...';
                btnSpinner.classList.remove('d-none');
                resultsDiv.innerHTML = '<div class="alert alert-info">正在執行預測Agent分析，請稍候...</div>';
                chartDiv.innerHTML = '';
                analysisDiv.innerHTML = '';
                recordsDiv.innerHTML = '';
                
                try {
                    const response = await fetch('/api/forecast-agent', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            type: type,
                            periods: periods
                        })
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        // 顯示預測結果
                        let html = '<div class="card mb-3">';
                        html += '<div class="card-header bg-success text-white">';
                        html += '<h5 class="mb-0"><i class="fas fa-chart-bar"></i> 預測結果</h5>';
                        html += '</div><div class="card-body">';
                        html += `<p><strong>執行時間：</strong>${data.execution_time}</p>`;
                        html += `<p><strong>預測類型：</strong>${data.forecast_type}</p>`;
                        html += `<p><strong>預測期數：</strong>${data.forecast_periods}</p>`;
                        html += `<p><strong>總預測銷售額：</strong>${data.total_forecast_sales}</p>`;
                        html += `<p><strong>平均銷售額：</strong>${data.avg_sales}</p>`;
                        html += `<p><strong>狀態：</strong><span class="badge bg-success">${data.status}</span></p>`;
                        html += '</div></div>';
                        resultsDiv.innerHTML = html;
                        
                        // 顯示圖表
                        if (data.chart_filename) {
                            chartDiv.innerHTML = `
                                <div class="card">
                                    <div class="card-header bg-primary text-white">
                                        <h5 class="mb-0"><i class="fas fa-chart-area"></i> 預測圖表</h5>
                                    </div>
                                    <div class="card-body text-center">
                                        <img src="/static/${data.chart_filename}" class="img-fluid" alt="預測圖表" 
                                             onerror="this.style.display='none'; this.parentElement.innerHTML='<p class=\'text-muted\'>圖表載入失敗</p>';">
                                    </div>
                                </div>
                            `;
                        }
                        
                        // 顯示AI分析
                        if (data.ai_analysis && data.ai_analysis.success) {
                            analysisDiv.innerHTML = `
                                <div class="card">
                                    <div class="card-header bg-info text-white">
                                        <h5 class="mb-0"><i class="fas fa-robot"></i> AI 分析報告</h5>
                                    </div>
                                    <div class="card-body">
                                        <div style="white-space: pre-wrap; font-family: 'Courier New', monospace; font-size: 14px; line-height: 1.6;">
                                            ${data.ai_analysis.analysis}
                                        </div>
                                    </div>
                                </div>
                            `;
                        }
                        
                        // 顯示歷史記錄
                        recordsDiv.innerHTML = `
                            <div class="card">
                                <div class="card-header bg-secondary text-white">
                                    <h5 class="mb-0"><i class="fas fa-clock"></i> 歷史預測記錄</h5>
                                </div>
                                <div class="card-body">
                                    <div class="table-responsive">
                                        <table class="table table-striped">
                                            <thead class="table-dark">
                                                <tr>
                                                    <th>執行時間</th>
                                                    <th>預測類型</th>
                                                    <th>預測期數</th>
                                                    <th>總預測銷售額</th>
                                                    <th>平均銷售額</th>
                                                    <th>狀態</th>
                                                    <th>操作</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr>
                                                    <td>${data.execution_time}</td>
                                                    <td>${data.forecast_type}</td>
                                                    <td>${data.forecast_periods}</td>
                                                    <td>${data.total_forecast_sales}</td>
                                                    <td>${data.avg_sales}</td>
                                                    <td><span class="badge bg-success">${data.status}</span></td>
                                                    <td><button class="btn btn-sm btn-primary"><i class="fas fa-eye"></i> 查看</button></td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        `;
                        
                    } else {
                        resultsDiv.innerHTML = `<div class="alert alert-danger">
                            <h4 class="alert-heading">預測Agent執行失敗</h4>
                            <p>${data.error}</p>
                        </div>`;
                    }
                } catch (error) {
                    resultsDiv.innerHTML = `<div class="alert alert-danger">
                        <h4 class="alert-heading">系統錯誤</h4>
                        <p>無法連接到伺服器或處理過程中發生錯誤。</p>
                        <hr>
                        <p class="mb-0">詳細錯誤：${error.message}</p>
                    </div>`;
                } finally {
                    // 恢復按鈕狀態
                    btn.disabled = false;
                    btnText.innerHTML = '<i class="fas fa-play"></i> 立即執行';
                    btnSpinner.classList.add('d-none');
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
    
    @app.route('/unified-forecast-test')
    def unified_forecast_test_page():
        """統一預測測試頁面"""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>統一預測系統測試</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <div class="row">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header bg-primary text-white">
                                <h3 class="mb-0">
                                    <i class="fas fa-chart-line"></i> 統一預測系統
                                </h3>
                                <p class="mb-0">結合業績預測細膩圖表 + AI 深度分析</p>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-6">
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
                                                <input class="form-check-input" type="checkbox" id="enableAiAnalysis" checked>
                                                <label class="form-check-label">啟用 AI 分析</label>
                                            </div>
                                        </div>
                                        <button onclick="generateUnifiedForecast()" id="generateBtn" class="btn btn-primary btn-lg">
                                            <span id="btnText">
                                                <i class="fas fa-chart-line"></i> 生成統一預測
                                            </span>
                                            <span id="btnSpinner" class="spinner-border spinner-border-sm d-none" role="status" aria-hidden="true"></span>
                                        </button>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="alert alert-info">
                                            <h6><i class="fas fa-info-circle"></i> 系統特色</h6>
                                            <ul class="mb-0">
                                                <li><strong>細膩圖表：</strong>使用 matplotlib 生成高品質靜態圖表</li>
                                                <li><strong>AI 分析：</strong>整合 Gemini API 進行深度業務分析</li>
                                                <li><strong>統一介面：</strong>單一 API 提供完整預測功能</li>
                                                <li><strong>數據一致性：</strong>統一的模型參數確保預測結果一致</li>
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div id="result" class="mt-4"></div>
                <div id="chart" class="mt-4"></div>
                <div id="analysis" class="mt-4"></div>
            </div>
            
            <script>
            async function generateUnifiedForecast() {
                const btn = document.getElementById('generateBtn');
                const btnText = document.getElementById('btnText');
                const btnSpinner = document.getElementById('btnSpinner');
                const resultDiv = document.getElementById('result');
                const chartDiv = document.getElementById('chart');
                const analysisDiv = document.getElementById('analysis');
                
                const type = document.getElementById('forecastType').value;
                const periods = parseInt(document.getElementById('periods').value);
                const enableAiAnalysis = document.getElementById('enableAiAnalysis').checked;
                
                // 驗證輸入
                if (periods < 1 || periods > 24) {
                    resultDiv.innerHTML = '<div class="alert alert-danger">預測期數必須在1到24之間</div>';
                    return;
                }
                
                // 更新按鈕狀態
                btn.disabled = true;
                btnText.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 生成中...';
                btnSpinner.classList.remove('d-none');
                resultDiv.innerHTML = '<div class="alert alert-info">正在生成統一預測結果，請稍候...</div>';
                chartDiv.innerHTML = '';
                analysisDiv.innerHTML = '';
                
                try {
                    const response = await fetch('/api/unified-forecast', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            type: type,
                            periods: periods,
                            enable_ai_analysis: enableAiAnalysis
                        })
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        // 顯示預測數據
                        let html = '<div class="row">';
                        
                        // 左側：預測數據
                        html += '<div class="col-md-6">';
                        html += '<div class="card mb-3"><div class="card-header bg-success text-white">';
                        html += '<h5 class="mb-0"><i class="fas fa-chart-bar"></i> 預測結果</h5>';
                        html += '</div><div class="card-body">';
                        html += `<p><strong>總預測銷售額：</strong>NT$ ${data.total_forecast.toLocaleString()}</p>`;
                        html += `<p><strong>平均月銷售額：</strong>NT$ ${data.avg_forecast.toLocaleString()}</p>`;
                        html += `<p><strong>預測期數：</strong>${data.periods} ${type}</p>`;
                        html += `<p><strong>預測範圍：</strong>${data.forecast_range}</p>`;
                        html += '</div></div>';
                        
                        html += '<div class="card"><div class="card-header bg-info text-white">';
                        html += '<h5 class="mb-0"><i class="fas fa-table"></i> 詳細預測數據</h5>';
                        html += '</div><div class="card-body">';
                        html += '<div class="table-responsive">';
                        html += '<table class="table table-striped table-hover">';
                        html += '<thead class="table-light"><tr><th>期間</th><th class="text-end">預測銷售額</th></tr></thead>';
                        html += '<tbody>';
                        data.forecast_data.forEach(item => {
                            html += `<tr><td>${item.period}</td><td class="text-end">NT$ ${item.forecast_sales.toLocaleString()}</td></tr>`;
                        });
                        html += '</tbody></table></div></div></div>';
                        html += '</div>';
                        
                        // 右側：模型資訊
                        html += '<div class="col-md-6">';
                        html += '<div class="card mb-3"><div class="card-header bg-warning text-white">';
                        html += '<h5 class="mb-0"><i class="fas fa-cogs"></i> 模型資訊</h5>';
                        html += '</div><div class="card-body">';
                        html += `<p><strong>模型類型：</strong>${data.model_info.model_type}</p>`;
                        html += `<p><strong>訓練期間：</strong>${data.model_info.training_period.start} - ${data.model_info.training_period.end}</p>`;
                        html += `<p><strong>參數：</strong>ARIMA(${data.model_info.parameters.order.join(',')}) × SARIMA(${data.model_info.parameters.seasonal_order.join(',')})</p>`;
                        html += `<p><strong>AIC：</strong>${data.model_info.model_summary.aic.toFixed(2)}</p>`;
                        html += `<p><strong>BIC：</strong>${data.model_info.model_summary.bic.toFixed(2)}</p>`;
                        html += '</div></div>';
                        
                        // 歷史數據統計
                        if (data.historical_data && data.historical_data.stats) {
                            const stats = data.historical_data.stats;
                            html += '<div class="card"><div class="card-header bg-secondary text-white">';
                            html += '<h5 class="mb-0"><i class="fas fa-history"></i> 歷史數據統計</h5>';
                            html += '</div><div class="card-body">';
                            html += `<p><strong>數據點數：</strong>${stats.data_points} 個月</p>`;
                            html += `<p><strong>總歷史銷售：</strong>NT$ ${stats.total_sales.toLocaleString()}</p>`;
                            html += `<p><strong>平均月銷售：</strong>NT$ ${stats.avg_monthly_sales.toLocaleString()}</p>`;
                            html += `<p><strong>銷售標準差：</strong>NT$ ${stats.sales_std.toLocaleString()}</p>`;
                            html += '</div></div>';
                        }
                        html += '</div>';
                        
                        html += '</div>';
                        resultDiv.innerHTML = html;
                        
                        // 顯示圖表
                        if (data.chart_filename) {
                            chartDiv.innerHTML = `
                                <div class="card">
                                    <div class="card-header bg-primary text-white">
                                        <h5 class="mb-0"><i class="fas fa-chart-area"></i> 統一預測圖表</h5>
                                    </div>
                                    <div class="card-body text-center">
                                        <img src="/static/${data.chart_filename}" class="img-fluid" alt="統一預測圖表" 
                                             onerror="this.style.display='none'; this.parentElement.innerHTML='<p class=\'text-muted\'>圖表載入失敗</p>';">
                                    </div>
                                </div>
                            `;
                        }
                        
                        // 顯示 AI 分析
                        if (data.ai_analysis && data.ai_analysis.success) {
                            analysisDiv.innerHTML = `
                                <div class="card">
                                    <div class="card-header bg-success text-white">
                                        <h5 class="mb-0"><i class="fas fa-robot"></i> AI 深度分析報告</h5>
                                    </div>
                                    <div class="card-body">
                                        <div style="white-space: pre-wrap; font-family: 'Courier New', monospace; font-size: 14px; line-height: 1.6;">
                                            ${data.ai_analysis.analysis}
                                        </div>
                                    </div>
                                </div>
                            `;
                        } else if (data.ai_analysis) {
                            analysisDiv.innerHTML = `
                                <div class="alert alert-warning">
                                    <i class="fas fa-exclamation-triangle"></i>
                                    AI 分析未執行：${data.ai_analysis.message || data.ai_analysis.error}
                                </div>
                            `;
                        }
                        
                    } else {
                        resultDiv.innerHTML = `<div class="alert alert-danger">
                            <h4 class="alert-heading">統一預測失敗</h4>
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
                    btnText.innerHTML = '<i class="fas fa-chart-line"></i> 生成統一預測';
                    btnSpinner.classList.add('d-none');
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