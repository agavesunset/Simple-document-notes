@echo off
chcp 65001 >nul
echo 正在卸载...

:: 清理 Mark
reg delete "HKCU\Software\Classes\*\shell\SpaceM_Mark" /f >nul 2>&1
reg delete "HKCU\Software\Classes\Directory\shell\SpaceM_Mark" /f >nul 2>&1

:: 清理 Clear
reg delete "HKCU\Software\Classes\*\shell\SpaceM_Clear" /f >nul 2>&1
reg delete "HKCU\Software\Classes\Directory\shell\SpaceM_Clear" /f >nul 2>&1

:: 清理快捷方式
del /q "%APPDATA%\Microsoft\Windows\SendTo\🏷️ SpaceM_Mark.lnk" >nul 2>&1

echo ✅ 卸载完成。
pause