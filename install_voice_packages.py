#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
語音播放功能套件安裝腳本
用於安裝 gTTS 和 pyttsx3 語音合成套件
"""

import subprocess
import sys
import os

def install_package(package_name, package_version=None):
    """安裝指定的套件"""
    try:
        if package_version:
            package_spec = f"{package_name}>={package_version}"
        else:
            package_spec = package_name
            
        print(f"正在安裝 {package_spec}...")
        
        # 使用 pip 安裝套件
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", package_spec
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {package_name} 安裝成功！")
            return True
        else:
            print(f"❌ {package_name} 安裝失敗：")
            print(f"錯誤訊息：{result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 安裝 {package_name} 時發生錯誤：{e}")
        return False

def check_package_installed(package_name):
    """檢查套件是否已安裝"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def test_voice_synthesis():
    """測試語音合成功能"""
    print("\n🔍 測試語音合成功能...")
    
    # 測試 gTTS
    gtts_available = False
    try:
        from gtts import gTTS
        from gtts.lang import tts_langs
        print("✅ gTTS 可用")
        gtts_available = True
        
        # 檢查支援的語言
        try:
            langs = tts_langs()
            if 'zh-tw' in langs:
                print("   - 支援繁體中文 (zh-tw)")
            elif 'zh' in langs:
                print("   - 支援簡體中文 (zh)")
            else:
                print("   - 不支援中文，將使用英文")
        except:
            print("   - 無法檢查語言支援")
            
    except ImportError:
        print("❌ gTTS 不可用")
    
    # 測試 pyttsx3
    pyttsx3_available = False
    try:
        import pyttsx3
        print("✅ pyttsx3 可用")
        pyttsx3_available = True
        
        # 檢查可用的語音
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            print(f"   - 找到 {len(voices)} 個語音")
            for i, voice in enumerate(voices[:3]):  # 只顯示前3個
                print(f"     {i+1}. {voice.name} ({voice.id})")
        except:
            print("   - 無法檢查語音列表")
            
    except ImportError:
        print("❌ pyttsx3 不可用")
    
    if gtts_available or pyttsx3_available:
        print("\n🎉 語音合成功能測試完成！")
        print("您現在可以使用語音播放功能了。")
        return True
    else:
        print("\n❌ 語音合成功能測試失敗！")
        print("請檢查安裝狀態或聯繫技術支援。")
        return False

def main():
    """主函數"""
    print("🎤 語音播放功能套件安裝腳本")
    print("=" * 50)
    
    # 檢查 Python 版本
    python_version = sys.version_info
    print(f"Python 版本：{python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 7):
        print("❌ 需要 Python 3.7 或更高版本")
        return
    
    print("✅ Python 版本符合要求")
    
    # 檢查已安裝的套件
    print("\n🔍 檢查已安裝的套件...")
    
    gtts_installed = check_package_installed('gtts')
    pyttsx3_installed = check_package_installed('pyttsx3')
    
    if gtts_installed:
        print("✅ gTTS 已安裝")
    else:
        print("❌ gTTS 未安裝")
    
    if pyttsx3_installed:
        print("✅ pyttsx3 已安裝")
    else:
        print("❌ pyttsx3 未安裝")
    
    # 安裝缺失的套件
    print("\n📦 開始安裝套件...")
    
    packages_to_install = []
    
    if not gtts_installed:
        packages_to_install.append(('gtts', '2.3.0'))
    
    if not pyttsx3_installed:
        packages_to_install.append(('pyttsx3', '2.90'))
    
    if not packages_to_install:
        print("✅ 所有必要套件都已安裝！")
    else:
        print(f"需要安裝 {len(packages_to_install)} 個套件")
        
        for package_name, package_version in packages_to_install:
            success = install_package(package_name, package_version)
            if not success:
                print(f"⚠️  {package_name} 安裝失敗，但可以繼續安裝其他套件")
    
    # 測試語音合成功能
    test_voice_synthesis()
    
    print("\n" + "=" * 50)
    print("📚 安裝說明：")
    print("1. 如果所有套件都安裝成功，您就可以使用語音播放功能了")
    print("2. 如果安裝失敗，請檢查網路連線和 pip 設定")
    print("3. 在 Windows 上，pyttsx3 可能需要額外的系統依賴")
    print("4. 如果遇到問題，請參考 '語音播放功能說明.md' 文件")
    
    print("\n🔗 相關資源：")
    print("- gTTS 官方文檔：https://gtts.readthedocs.io/")
    print("- pyttsx3 官方文檔：https://pyttsx3.readthedocs.io/")
    print("- 語音播放功能說明：語音播放功能說明.md")

if __name__ == "__main__":
    main()
