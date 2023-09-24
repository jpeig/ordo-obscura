cd "C:\AI\obscura\obscura\Scripts"
call activate
cd "C:\AI\obscura\obscura"
echo You are now in the directory: %cd%
start /b python obscura.py
timeout /t 2
start http://127.0.0.1:8001