"""
Script for building EXE file from Python application
Uses PyInstaller to create executable file
"""
import subprocess
import sys
import os
from pathlib import Path

def build_exe():
    """Builds EXE file from application"""
    print("🔨 Начинаю сборку EXE файла...")
    
    client_secret_path = Path(__file__).parent / "client_secret.json"
    oauth_config_path = Path(__file__).parent / "oauth_config.py"
    original_content = None
    secret_b64 = None
    
    if client_secret_path.exists():
        import base64
        with open(client_secret_path, 'rb') as f:
            secret_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        with open(oauth_config_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        old_line = '    EMBEDDED_CLIENT_SECRET_B64 = ""'
        new_line = f'    EMBEDDED_CLIENT_SECRET_B64 = "{secret_b64}"'
        
        if old_line in original_content:
            content = original_content.replace(old_line, new_line)
            with open(oauth_config_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("🔐 Base64 ключ встроен в код (безопасно)")
    
    try:
        import PyInstaller
    except ImportError:
        print("❌ PyInstaller не установлен!")
        print("📦 Устанавливаю PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller установлен!")
    
    main_script = Path(__file__).parent / "main.py"
    
    if not main_script.exists():
        print(f"❌ Файл {main_script} не найден!")
        return False
    
    spec_file = Path(__file__).parent / "MyAI_Clean.spec"
    
    if spec_file.exists():
        print("📋 Использую spec файл для сборки...")
        cmd = ["pyinstaller", "--clean", str(spec_file)]
    else:
        print("📋 Использую автоматическую сборку...")
        cmd = [
            "pyinstaller",
            "--name=MyAI_Clean",
            "--onefile",
            "--windowed",
            "--icon=NONE",
            "--add-data=locales;locales",
            "--hidden-import=customtkinter",
            "--hidden-import=PIL",
            "--hidden-import=cv2",
            "--hidden-import=torch",
            "--hidden-import=sentence_transformers",
            "--hidden-import=google",
            "--hidden-import=google.auth",
            "--hidden-import=google.oauth2",
            "--hidden-import=googleapiclient",
            "--collect-all=customtkinter",
            "--collect-all=PIL",
            str(main_script)
        ]
    
    print(f"🚀 Запускаю PyInstaller...")
    print(f"📝 Команда: {' '.join(cmd)}")
    print("⏳ Это может занять несколько минут...")
    
    try:
        subprocess.check_call(cmd)
        print("\n✅ Сборка завершена успешно!")
        
        if original_content and oauth_config_path.exists():
            with open(oauth_config_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            print("🔄 oauth_config.py восстановлен в исходное состояние")
        
        exe_path = Path(__file__).parent / "dist" / "MyAI_Clean.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📦 EXE файл находится в: {exe_path}")
            print(f"📊 Размер файла: {size_mb:.1f} MB")
            print("\n✅ Готово! EXE файл содержит встроенный ключ (base64)")
            print("💡 При первом запуске автоматически создастся client_secret.json")
            print("📤 Отправьте другу только EXE файл - всё работает автоматически!")
            print("⚠️  Внимание: EXE файл может быть большим из-за включенных библиотек (PyTorch, OpenCV и т.д.)")
        else:
            print("⚠️  EXE файл не найден в dist/")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка при сборке: {e}")
        if original_content and oauth_config_path.exists():
            with open(oauth_config_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            print("🔄 oauth_config.py восстановлен в исходное состояние")
        return False
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        if original_content and oauth_config_path.exists():
            with open(oauth_config_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            print("🔄 oauth_config.py восстановлен в исходное состояние")
        return False

if __name__ == "__main__":
    success = build_exe()
    sys.exit(0 if success else 1)

