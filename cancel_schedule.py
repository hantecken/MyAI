#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡單的取消排程腳本
"""

from scheduler import cancel_schedule, get_schedule_status

def main():
    """取消排程"""
    print("🔄 取消排程中...")
    
    # 顯示當前狀態
    status = get_schedule_status()
    print(f"當前狀態: {status['status']}")
    
    # 取消排程
    if cancel_schedule():
        print("✅ 排程已成功取消")
        
        # 顯示新狀態
        new_status = get_schedule_status()
        print(f"新狀態: {new_status['status']}")
        print(f"訊息: {new_status['message']}")
    else:
        print("❌ 取消排程失敗")

if __name__ == "__main__":
    main() 