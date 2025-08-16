#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
檢查排程器狀態
"""

import json
import os
from datetime import datetime
from scheduler import ForecastScheduler, get_schedule_status

def check_scheduler_status():
    """檢查排程器狀態"""
    print("🔍 檢查排程器狀態...")
    print("=" * 50)
    
    # 檢查設定檔案
    config_file = 'schedule_config.json'
    if os.path.exists(config_file):
        print(f"✅ 設定檔案存在: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print("\n📋 當前設定:")
        print(f"  執行頻率: {config.get('schedule_type', 'N/A')}")
        print(f"  執行時間: {config.get('execution_time', 'N/A')}")
        print(f"  郵件通知: {'啟用' if config.get('email_notification') else '停用'}")
        print(f"  收件人: {config.get('email_recipients', 'N/A')}")
        
    else:
        print(f"❌ 設定檔案不存在: {config_file}")
    
    # 檢查排程狀態
    print("\n🔄 排程運行狀態:")
    status = get_schedule_status()
    print(f"  狀態: {status['status']}")
    print(f"  訊息: {status['message']}")
    
    if status['status'] == 'active':
        print("  ✅ 排程正在運行中")
    elif status['status'] == 'paused':
        print("  ⏸️ 排程已暫停")
    elif status['status'] == 'disabled':
        print("  ❌ 排程已停用")
    
    # 檢查 static 目錄
    static_dir = 'static'
    if os.path.exists(static_dir):
        print(f"\n✅ 圖表目錄存在: {static_dir}")
        
        # 檢查圖表檔案
        chart_files = [f for f in os.listdir(static_dir) if f.startswith('forecast_chart_')]
        if chart_files:
            print(f"📊 找到 {len(chart_files)} 個預測圖表:")
            for file in sorted(chart_files, reverse=True)[:5]:  # 顯示最新的5個
                file_path = os.path.join(static_dir, file)
                file_size = os.path.getsize(file_path)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                print(f"  - {file} ({file_size/1024:.1f}KB, {file_time.strftime('%Y-%m-%d %H:%M:%S')})")
        else:
            print("📊 尚未生成預測圖表")
    else:
        print(f"❌ 圖表目錄不存在: {static_dir}")
    
    # 測試排程器功能
    print("\n🧪 測試排程器功能...")
    try:
        scheduler = ForecastScheduler()
        print("✅ 排程器實例化成功")
        
        # 顯示下次執行時間
        current_time = datetime.now()
        print(f"🕐 當前時間: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if config.get('schedule_type') == 'daily':
            print(f"📅 下次執行: 每日 {config.get('execution_time')}")
        elif config.get('schedule_type') == 'weekly':
            print(f"📅 下次執行: 每週一 {config.get('execution_time')}")
        elif config.get('schedule_type') == 'monthly':
            print(f"📅 下次執行: 每月1號 {config.get('execution_time')}")
        elif config.get('schedule_type') == 'none':
            print("📅 排程已停用")
            
    except Exception as e:
        print(f"❌ 排程器測試失敗: {e}")
    
    print("\n" + "=" * 50)
    print("✅ 排程器狀態檢查完成")
    
    # 顯示管理命令
    print("\n💡 排程管理命令:")
    print("  python schedule_manager.py status    # 查看狀態")
    print("  python schedule_manager.py cancel    # 取消排程")
    print("  python schedule_manager.py pause     # 暫停排程")
    print("  python schedule_manager.py resume    # 恢復排程")

if __name__ == "__main__":
    check_scheduler_status() 