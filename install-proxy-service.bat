@echo off
set NSSM="C:\Users\Moonga Dev\AppData\Local\Microsoft\WinGet\Packages\NSSM.NSSM_Microsoft.Winget.Source_8wekyb3d8bbwe\nssm-2.24-101-g897c7ad\win64\nssm.exe"
set UVICORN="C:\Users\Moonga Dev\AppData\Local\Programs\Python\Python312\Scripts\uvicorn.exe"
set APPDIR=C:\Moonga_agent\Dev Projects\privateLLM

%NSSM% install PrivateLLMProxy %UVICORN% "server:app --host 0.0.0.0 --port 8000"
%NSSM% set PrivateLLMProxy AppDirectory "%APPDIR%"
%NSSM% set PrivateLLMProxy AppEnvironmentExtra "LLM_API_KEY=PN30ZENng6XE09CJ_n5VUnIBcBfbKWPkO0XGJaLvfUo"
%NSSM% set PrivateLLMProxy Start SERVICE_AUTO_START
sc start PrivateLLMProxy

echo Done.
pause
