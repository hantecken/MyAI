#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
排程管理工具
提供取消、暫停、恢復和查看排程狀態的功能
"""

import sys
import json
from datetime import datetime
from scheduler import (
    cancel_schedule, 
    pause_schedule, 
    resume_schedule, 
    get_schedule_status,
    forecast_scheduler
)

def show_help():
    """顯示使用說明"""
    print("""
📋 排程管理工具使用說明

用法: python schedule_manager.py [命令]

可用命令:
  status     - 查看排程狀態
  cancel     - 取消所有排程（永久停用）
  pause      - 暫停排程（保留設定）
  resume     - 恢復排程
  help       - 顯示此說明

範例:
  python schedule_manager.py status    # 查看狀態
  python schedule_manager.py cancel    # 取消排程
  python schedule_manager.py pause     # 暫停排程
  python schedule_manager.py resume    # 恢復排程
""")

def show_status():
    """顯示排程狀態"""
    print("🔍 檢查排程狀態...")
    print("=" * 50)
    
    status = get_schedule_status()
    
    print(f"📋 狀態: {status['status']}")
    print(f"💬 訊息: {status['message']}")
    
    if status['status'] == 'active':
        print(f"📅 執行頻率: {status.get('schedule_type', 'N/A')}")
        print(f"🕐 執行時間: {status.get('execution_time', 'N/A')}")
        print("✅ 排程正在運行中")
        
    elif status['status'] == 'paused':
        print(f"📅 執行頻率: {status.get('schedule_type', 'N/A')}")
        print(f"🕐 執行時間: {status.get('execution_time', 'N/A')}")
        print("⏸️ 排程已暫停，可使用 'resume' 恢復")
        
    elif status['status'] == 'disabled':
        print("❌ 排程已停用，需要重新設定")
        
    elif status['status'] == 'error':
        print(f"❌ 錯誤: {status['message']}")
    
    print("=" * 50)

def cancel_schedule_command():
    """取消排程命令"""
    print("⚠️ 確定要取消所有排程嗎？")
    print("此操作將永久停用排程，需要重新設定才能恢復。")
    
    response = input("請輸入 'yes' 確認取消: ").strip().lower()
    
    if response == 'yes':
        if cancel_schedule():
            print("✅ 排程已成功取消")
            show_status()
        else:
            print("❌ 取消排程失敗")
    else:
        print("❌ 操作已取消")

def pause_schedule_command():
    """暫停排程命令"""
    print("⏸️ 暫停排程...")
    if pause_schedule():
        print("✅ 排程已暫停")
        show_status()
    else:
        print("❌ 暫停排程失敗")

def resume_schedule_command():
    """恢復排程命令"""
    print("▶️ 恢復排程...")
    if resume_schedule():
        print("✅ 排程已恢復")
        show_status()
    else:
        print("❌ 恢復排程失敗")

def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("❌ 請提供命令")
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'status':
        show_status()
    elif command == 'cancel':
        cancel_schedule_command()
    elif command == 'pause':
        pause_schedule_command()
    elif command == 'resume':
        resume_schedule_command()
    elif command == 'help':
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main() 