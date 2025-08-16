#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
語音播放功能測試腳本
用於測試語音合成和播放功能
"""

import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_voice_synthesis():
    """測試語音合成功能"""
    print("🔍 測試語音合成功能...")
    
    try:
        # 測試 gTTS
        print("\n1. 測試 gTTS...")
        try:
            from gtts import gTTS
            from gtts.lang import tts_langs
            
            # 檢查支援的語言
            langs = tts_langs()
            print(f"   ✅ gTTS 可用，支援 {len(langs)} 種語言")
            
            if 'zh-tw' in langs:
                print("   ✅ 支援繁體中文 (zh-tw)")
                test_lang = 'zh-tw'
            elif 'zh' in langs:
                print("   ✅ 支援簡體中文 (zh)")
                test_lang = 'zh'
            else:
                print("   ⚠️ 不支援中文，使用英文測試")
                test_lang = 'en'
            
            # 測試語音合成
            test_text = "測試語音合成功能，這是一個中文語音測試。"
            if test_lang == 'en':
                test_text = "Testing voice synthesis function, this is a test."
            
            print(f"   測試文字：{test_text}")
            print("   正在生成語音文件...")
            
            tts = gTTS(text=test_text, lang=test_lang, slow=False)
            test_file = "test_voice_gtts.mp3"
            tts.save(test_file)
            
            if os.path.exists(test_file):
                print(f"   ✅ 語音文件生成成功：{test_file}")
                print(f"   文件大小：{os.path.getsize(test_file)} 字節")
                
                # 清理測試文件
                os.remove(test_file)
                print("   🗑️ 測試文件已清理")
            else:
                print("   ❌ 語音文件生成失敗")
                
        except ImportError:
            print("   ❌ gTTS 未安裝")
        except Exception as e:
            print(f"   ❌ gTTS 測試失敗：{e}")
        
        # 測試 pyttsx3
        print("\n2. 測試 pyttsx3...")
        try:
            import pyttsx3
            
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            print(f"   ✅ pyttsx3 可用，找到 {len(voices)} 個語音")
            
            # 顯示可用的語音
            for i, voice in enumerate(voices[:5]):  # 只顯示前5個
                print(f"     {i+1}. {voice.name} ({voice.id})")
            
            # 測試語音合成
            test_text = "測試語音合成功能，這是一個中文語音測試。"
            print(f"   測試文字：{test_text}")
            print("   正在生成語音文件...")
            
            test_file = "test_voice_pyttsx3.wav"
            engine.save_to_file(test_text, test_file)
            engine.runAndWait()
            
            if os.path.exists(test_file):
                print(f"   ✅ 語音文件生成成功：{test_file}")
                print(f"   文件大小：{os.path.getsize(test_file)} 字節")
                
                # 清理測試文件
                os.remove(test_file)
                print("   🗑️ 測試文件已清理")
            else:
                print("   ❌ 語音文件生成失敗")
                
        except ImportError:
            print("   ❌ pyttsx3 未安裝")
        except Exception as e:
            print(f"   ❌ pyttsx3 測試失敗：{e}")
        
        print("\n🎉 語音合成功能測試完成！")
        
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤：{e}")

def test_voice_controller():
    """測試語音控制器功能"""
    print("\n🔍 測試語音控制器功能...")
    
    try:
        # 測試分析控制器中的語音功能
        from controllers.analysis_controller import AnalysisController
        
        # 創建一個模擬的數據管理器
        class MockDataManager:
            pass
        
        controller = AnalysisController(MockDataManager())
        
        # 測試語音總結生成
        test_summary = """
        📊 <strong>主要貢獻分析：</strong>
        <strong>產品A</strong>貢獻了 100,000 元，
        <strong>產品B</strong>貢獻了 80,000 元
        
        🔎 <strong>其他維度參考分析：</strong><br>
        <b>業務員 維度影響：</b> 王小明（差異：+50,000元）; 李美麗（差異：+30,000元）<br>
        <b>客戶 維度影響：</b> 陳先生（差異：+40,000元）; 林小姐（差異：+20,000元）
        """
        
        print("   測試分析總結：")
        print(f"   {test_summary[:100]}...")
        
        # 測試語音總結生成
        result = controller.generate_voice_summary(test_summary)
        
        if result['success']:
            print("   ✅ 語音總結生成成功")
            print(f"   語音內容：{result['voice_content']}")
            print(f"   主要貢獻：{result['main_contribution']}")
            print(f"   其他維度：{result['other_dimension']}")
            
            if result['audio_file_path']:
                print(f"   音頻文件：{result['audio_file_path']}")
                
                # 檢查文件是否存在
                if os.path.exists(result['audio_file_path']):
                    print(f"   ✅ 音頻文件存在，大小：{os.path.getsize(result['audio_file_path'])} 字節")
                    
                    # 清理測試文件
                    os.remove(result['audio_file_path'])
                    print("   🗑️ 測試文件已清理")
                else:
                    print("   ❌ 音頻文件不存在")
            else:
                print("   ⚠️ 未生成音頻文件")
        else:
            print(f"   ❌ 語音總結生成失敗：{result['error']}")
        
        # 測試語音狀態檢查
        status_result = controller.get_voice_summary_status()
        if status_result['success']:
            print("   ✅ 語音狀態檢查成功")
            print(f"   語音合成可用：{status_result['voice_synthesis_available']}")
            print(f"   gTTS 可用：{status_result['gtts_available']}")
            print(f"   pyttsx3 可用：{status_result['pyttsx3_available']}")
        else:
            print(f"   ❌ 語音狀態檢查失敗：{status_result['error']}")
        
        print("\n🎉 語音控制器功能測試完成！")
        
    except ImportError as e:
        print(f"   ❌ 無法導入分析控制器：{e}")
    except Exception as e:
        print(f"   ❌ 測試過程中發生錯誤：{e}")

def main():
    """主函數"""
    print("🎤 語音播放功能測試腳本")
    print("=" * 50)
    
    # 檢查 Python 版本
    python_version = sys.version_info
    print(f"Python 版本：{python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 7):
        print("❌ 需要 Python 3.7 或更高版本")
        return
    
    print("✅ Python 版本符合要求")
    
    # 執行測試
    test_voice_synthesis()
    test_voice_controller()
    
    print("\n" + "=" * 50)
    print("📚 測試結果說明：")
    print("1. 如果所有測試都通過，語音播放功能應該可以正常使用")
    print("2. 如果某些測試失敗，請檢查套件安裝狀態")
    print("3. 建議在實際使用前先運行此測試腳本")
    print("4. 如果遇到問題，請參考 '語音播放功能說明.md' 文件")

if __name__ == "__main__":
    main()
