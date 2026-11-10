@echo off
set NSSM=C:\Users\Moonga Dev\AppData\Local\Microsoft\WinGet\Packages\NSSM.NSSM_Microsoft.Winget.Source_8wekyb3d8bbwe\nssm-2.24-101-g897c7ad\win64\nssm.exe

echo [1/2] Fixing cloudflared service...
sc stop cloudflared
timeout /t 2 /nobreak >nul
sc config cloudflared binPath= "\"C:\Moonga_agent\Dev Projects\privateLLM\cloudflared.exe\" tunnel --config \"C:\Users\Moonga Dev\.cloudflared\config.yml\" run signal-llm"
sc start cloudflared

echo [2/2] Fixing PrivateLLMProxy service working directory...
sc stop PrivateLLMProxy
timeout /t 2 /nobreak >nul
"%NSSM%" set PrivateLLMProxy AppDirectory "C:\Moonga_agent\Dev Projects\privateLLM"
sc start PrivateLLMProxy

timeout /t 5 /nobreak >nul
curl -s https://llm.minnal.io/health
pause
