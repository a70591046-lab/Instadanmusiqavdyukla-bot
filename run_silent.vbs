Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\User\.gemini\antigravity\scratch\telegram_downloader_bot"
WshShell.Run "python main.py", 0, False
