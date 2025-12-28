@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo ==========================================
echo      正在安装 [SpaceM_Mark] 终极版
echo ==========================================

set "CURRENT_DIR=%~dp0"
set "CURRENT_DIR=%CURRENT_DIR:~0,-1%"
set "EXE_PATH=%CURRENT_DIR%\mark_hero.exe"

if not exist "%EXE_PATH%" (
    echo [错误] 找不到 mark_hero.exe
    pause
    exit /b
)

echo [1/2] 正在清理旧版菜单...
:: 先删掉那个单独的删除菜单，防止残留
reg delete "HKCU\Software\Classes\*\shell\SpaceM_Clear" /f >nul 2>&1
reg delete "HKCU\Software\Classes\Directory\shell\SpaceM_Clear" /f >nul 2>&1

echo [2/2] 注册标准菜单...

:: 只有这一个菜单，进去后既能看，也能加，也能删
reg add "HKCU\Software\Classes\*\shell\SpaceM_Mark" /ve /d "🏷️ SpaceM_Mark" /f >nul
reg add "HKCU\Software\Classes\*\shell\SpaceM_Mark\command" /ve /d "\"%EXE_PATH%\" \"%%1\"" /f >nul

:: 文件夹
reg add "HKCU\Software\Classes\Directory\shell\SpaceM_Mark" /ve /d "🏷️ SpaceM_Mark" /f >nul
reg add "HKCU\Software\Classes\Directory\shell\SpaceM_Mark\command" /ve /d "\"%EXE_PATH%\" \"%%1\"" /f >nul

echo [3/3] 注册快捷方式...
set "VBS_SCRIPT=%TEMP%\CreateSendTo_final.vbs"
set "SENDTO_FOLDER=%APPDATA%\Microsoft\Windows\SendTo"
set "LINK_NAME=🏷️ SpaceM_Mark.lnk"

(
echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
echo sLinkFile = "%SENDTO_FOLDER%\%LINK_NAME%"
echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
echo oLink.TargetPath = "%EXE_PATH%"
echo oLink.IconLocation = "%EXE_PATH%, 0"
echo oLink.WorkingDirectory = "%CURRENT_DIR%"
echo oLink.Save
) > "%VBS_SCRIPT%"
cscript /nologo "%VBS_SCRIPT%"
del "%VBS_SCRIPT%"

echo.
echo ==========================================
echo           ✅ 升级完毕！
echo ==========================================
echo.
echo 现在右键只有一个 "SpaceM_Mark"。
echo 点进去，每一条历史记录旁边都有个 [❌] 按钮。
echo 想删哪条删哪条！
echo.
pause