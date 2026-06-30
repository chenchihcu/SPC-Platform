Set WshShell = CreateObject("WScript.Shell")
Dim fso, pythonPath, scriptPath, currentDir, venvPythonw
Set fso = CreateObject("Scripting.FileSystemObject")

' Get current directory of the script
currentDir = fso.GetParentFolderName(WScript.ScriptPosition)
scriptPath = currentDir & "\main.py"

' Prioritize virtual environment pythonw.exe
venvPythonw = currentDir & "\.venv\Scripts\pythonw.exe"

If fso.FileExists(venvPythonw) Then
    pythonPath = venvPythonw
Else
    pythonPath = "pythonw"
End If

' Run pythonw with window style 0 (hidden) and waitOnReturn as False
WshShell.Run Chr(34) & pythonPath & Chr(34) & " " & Chr(34) & scriptPath & Chr(34), 0, False
