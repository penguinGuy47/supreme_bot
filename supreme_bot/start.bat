@echo off
cd C:\Users\%USERNAME%\Desktop\Code\Python\supreme_bot || (echo "Failed to navigate to the project directory" & pause & exit) 
call .\myenv\Scripts\activate || (echo "Failed to activate virtual environment" & pause & exit) 
python main.py 
pause