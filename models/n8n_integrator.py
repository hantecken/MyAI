import requests
import json
from datetime import datetime
import os

class N8nIntegrator:
    """
    N8n整合器類，負責與n8n進行通訊
    """
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send_forecast_result(self, forecast_data, plot_path):
        """
        發送預測結果到n8n webhook
        """
        try:
            # 構建消息內容
            message = self._format_forecast_message(forecast_data)
            
            # 準備發送的數據
            payload = {
                'message': message,
                'plot_path': plot_path,
                'timestamp': datetime.now().isoformat()
            }
            
            # 發送到webhook
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"發送預測結果到n8n時發生錯誤：{str(e)}")
            return False
    
    def _format_forecast_message(self, forecast_data):
        """
        格式化預測消息
        """
        message = "📊 業績預測結果\n\n"
        
        # 添加預測期間
        message += f"預測類型：{forecast_data['forecast_type']}\n"
        message += f"預測期數：{len(forecast_data['forecast_data'])}\n\n"
        
        # 添加預測數據
        message += "預測詳情：\n"
        for item in forecast_data['forecast_data']:
            message += f"- {item['period']}: {item['forecast_sales']:,.0f} 元\n"
        
        # 添加模型信息
        if 'model_info' in forecast_data:
            message += f"\n模型：{forecast_data['model_info']['method']}"
        
        return message
