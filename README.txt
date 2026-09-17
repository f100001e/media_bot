media_bot startup

1. Open WSL

   wsl

2. Start Redis

   sudo service redis-server start

3. Verify Redis

   redis-cli ping

   Expected:
   PONG

4. Start Ollama

   ollama serve

   If this is the first setup, or if the model is missing:

   ollama pull llama3

   Verify installed models:

   ollama list

   Leave WSL running while media_bot is running.

5. In a separate PowerShell terminal, activate the project environment

   cd C:\Projects\media_bot
   .\.venv\Scripts\Activate.ps1

6. Start media_bot

   python run.py

7. Open dashboard

   http://127.0.0.1:8000/queue