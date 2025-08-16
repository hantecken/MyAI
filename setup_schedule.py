#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新設定排程腳本
"""

import json
from scheduler import forecast_scheduler

def setup_daily_schedule():
    """設定每日排程"""
    print("📅 設定每日排程...")
    
    config = {
        'schedule_type': 'daily',
        'execution_time': '08:00',
        'email_notification': True,
        'email_recipients': 'test@example.com'
    }
    
    if forecast_scheduler.add_schedule(config):
        print("✅ 每日排程設定成功")
        print(f"📋 執行時間: {config['execution_time']}")
        print(f"📧 郵件通知: {'啟用' if config['email_notification'] else '停用'}")
        return True
    else:
        print("❌ 排程設定失敗")
        return False

def setup_weekly_schedule():
    """設定每週排程"""
    print("📅 設定每週排程...")
    
    config = {
        'schedule_type': 'weekly',
        'execution_time': '08:00',
        'email_notification': True,
        'email_recipients': 'test@example.com'
    }
    
    if forecast_scheduler.add_schedule(config):
        print("✅ 每週排程設定成功")
        print(f"📋 執行時間: 每週一 {config['execution_time']}")
        print(f"📧 郵件通知: {'啟用' if config['email_notification'] else '停用'}")
        return True
    else:
        print("❌ 排程設定失敗")
        return False

def setup_monthly_schedule():
    """設定每月排程"""
    print("📅 設定每月排程...")
    
    config = {
        'schedule_type': 'monthly',
        'execution_time': '08:00',
        'monthly_day': 1,
        'email_notification': True,
        'email_recipients': 'test@example.com'
    }
    
    if forecast_scheduler.add_schedule(config):
        print("✅ 每月排程設定成功")
        print(f"📋 執行時間: 每月1號 {config['execution_time']}")
        print(f"📧 郵件通知: {'啟用' if config['email_notification'] else '停用'}")
        return True
    else:
        print("❌ 排程設定失敗")
        return False

def main():
    """主函數"""
    print("🔄 排程設定工具")
    print("=" * 30)
    print("請選擇排程類型：")
    print("1. 每日排程")
    print("2. 每週排程")
    print("3. 每月排程")
    print("4. 退出")
    
    while True:
        choice = input("\n請輸入選項 (1-4): ").strip()
        
        if choice == '1':
            setup_daily_schedule()
            break
        elif choice == '2':
            setup_weekly_schedule()
            break
        elif choice == '3':
            setup_monthly_schedule()
            break
        elif choice == '4':
            print("❌ 操作已取消")
            break
        else:
            print("❌ 無效選項，請重新輸入")

if __name__ == "__main__":
    main() 