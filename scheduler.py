# 定期預測排程器
import schedule
import time
import threading
import json
import os
from datetime import datetime
import subprocess
import sys
from flask import Flask
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

class ForecastScheduler:
    def __init__(self):
        self.config_file = 'schedule_config.json'
        self.load_schedule_config()
        
    def load_schedule_config(self):
        """載入排程設定"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = {}
        except Exception as e:
            print(f"載入排程設定失敗: {e}")
            self.config = {}
    
    def save_schedule_config(self, config):
        """儲存排程設定"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.config = config
            return True
        except Exception as e:
            print(f"儲存排程設定失敗: {e}")
            return False
    
    def execute_forecast(self, config):
        """執行預測任務"""
        try:
            print(f"🕐 [{datetime.now()}] 開始執行定期預測...")
            
            # 執行預測
            result = subprocess.run([
                sys.executable, 'forecast_agent.py'
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode == 0:
                print(f"✅ [{datetime.now()}] 預測執行成功")
                
                # 解析圖表檔案名
                output_lines = result.stdout.split('\n')
                chart_filename = None
                for line in output_lines:
                    if '預測圖表已保存：' in line:
                        full_path = line.split('：')[1].strip()
                        chart_filename = os.path.basename(full_path)
                        break
                
                # 發送郵件通知
                if config.get('email_notification') and config.get('email_recipients'):
                    self.send_email_notification(config, chart_filename)
                    
            else:
                print(f"❌ [{datetime.now()}] 預測執行失敗: {result.stderr}")
                
        except Exception as e:
            print(f"❌ [{datetime.now()}] 執行預測時發生錯誤: {e}")
    
    def send_email_notification(self, config, chart_filename):
        """發送郵件通知"""
        try:
            # 這裡需要設定SMTP伺服器資訊
            # 目前使用模擬發送
            recipients = config.get('email_recipients', '').split(',')
            
            print(f"📧 [{datetime.now()}] 發送郵件通知給: {recipients}")
            print(f"📊 預測圖表: {chart_filename}")
            
            # 實際的郵件發送邏輯（需要設定SMTP）
            # self._send_email(recipients, chart_filename)
            
        except Exception as e:
            print(f"❌ [{datetime.now()}] 發送郵件失敗: {e}")
    
    def setup_schedule(self, config):
        """設定排程"""
        try:
            schedule_type = config.get('schedule_type')
            execution_time = config.get('execution_time', '08:00')
            
            if schedule_type == 'daily':
                schedule.every().day.at(execution_time).do(self.execute_forecast, config)
                print(f"📅 設定每日執行: {execution_time}")
                
            elif schedule_type == 'weekly':
                schedule.every().monday.at(execution_time).do(self.execute_forecast, config)
                print(f"📅 設定每週執行: 週一 {execution_time}")
                
            elif schedule_type == 'monthly':
                monthly_day = int(config.get('monthly_day', 1))
                schedule.every().month.at(execution_time).do(self.execute_forecast, config)
                print(f"📅 設定每月執行: {monthly_day}號 {execution_time}")
            
            return True
            
        except Exception as e:
            print(f"❌ 設定排程失敗: {e}")
            return False
    
    def cancel_schedule(self):
        """取消所有排程"""
        try:
            # 清除所有排程
            schedule.clear()
            
            # 清空設定檔案
            empty_config = {
                'schedule_type': 'none',
                'execution_time': '',
                'email_notification': False,
                'email_recipients': ''
            }
            
            if self.save_schedule_config(empty_config):
                print("✅ 已取消所有排程")
                print("📋 排程狀態: 已停用")
                return True
            else:
                print("❌ 取消排程失敗")
                return False
                
        except Exception as e:
            print(f"❌ 取消排程時發生錯誤: {e}")
            return False
    
    def pause_schedule(self):
        """暫停排程（不清除設定）"""
        try:
            # 清除所有排程但保留設定
            schedule.clear()
            print("⏸️ 排程已暫停")
            print("📋 設定已保留，可使用 resume_schedule() 重新啟動")
            return True
            
        except Exception as e:
            print(f"❌ 暫停排程時發生錯誤: {e}")
            return False
    
    def resume_schedule(self):
        """恢復排程"""
        try:
            if self.config and self.config.get('schedule_type') != 'none':
                if self.setup_schedule(self.config):
                    print("▶️ 排程已恢復")
                    return True
            else:
                print("❌ 沒有可恢復的排程設定")
                return False
                
        except Exception as e:
            print(f"❌ 恢復排程時發生錯誤: {e}")
            return False
    
    def get_schedule_status(self):
        """獲取排程狀態"""
        try:
            if not self.config or self.config.get('schedule_type') == 'none':
                return {
                    'status': 'disabled',
                    'message': '排程已停用'
                }
            
            # 檢查是否有活躍的排程
            if schedule.jobs:
                return {
                    'status': 'active',
                    'schedule_type': self.config.get('schedule_type'),
                    'execution_time': self.config.get('execution_time'),
                    'message': f"排程運行中: {self.config.get('schedule_type')} {self.config.get('execution_time')}"
                }
            else:
                return {
                    'status': 'paused',
                    'schedule_type': self.config.get('schedule_type'),
                    'execution_time': self.config.get('execution_time'),
                    'message': '排程已暫停'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f'獲取狀態失敗: {e}'
            }
    
    def start_scheduler(self):
        """啟動排程器"""
        print("🚀 啟動定期預測排程器...")
        
        # 載入現有設定並設定排程
        self.load_schedule_config()
        if self.config and self.config.get('schedule_type') != 'none':
            self.setup_schedule(self.config)
        
        # 持續運行排程器
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分鐘檢查一次
    
    def add_schedule(self, config):
        """添加新的排程"""
        try:
            # 清除現有排程
            schedule.clear()
            
            # 儲存新設定
            if self.save_schedule_config(config):
                # 設定新排程
                if self.setup_schedule(config):
                    print(f"✅ 排程設定成功: {config.get('schedule_type')} {config.get('execution_time')}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"❌ 添加排程失敗: {e}")
            return False

# 全域排程器實例
forecast_scheduler = ForecastScheduler()

def start_scheduler_thread():
    """在背景執行緒中啟動排程器"""
    scheduler_thread = threading.Thread(target=forecast_scheduler.start_scheduler, daemon=True)
    scheduler_thread.start()
    print("🔄 排程器已在背景啟動")

def cancel_schedule():
    """取消排程的便捷函數"""
    return forecast_scheduler.cancel_schedule()

def pause_schedule():
    """暫停排程的便捷函數"""
    return forecast_scheduler.pause_schedule()

def resume_schedule():
    """恢復排程的便捷函數"""
    return forecast_scheduler.resume_schedule()

def get_schedule_status():
    """獲取排程狀態的便捷函數"""
    return forecast_scheduler.get_schedule_status() 