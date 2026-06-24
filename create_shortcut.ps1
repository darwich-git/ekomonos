$TargetFile = "C:\Users\darwi.PCDARWICH\AppData\Local\Programs\Python\Python312\pythonw.exe"
$ShortcutFile = "$([Environment]::GetFolderPath('Desktop'))\Ekomonos V3.0.lnk"
$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutFile)
$Shortcut.TargetPath = $TargetFile
$Shortcut.Arguments = "d:\Proyectos\EKKOMONOS\main.py"
$Shortcut.WorkingDirectory = "d:\Proyectos\EKKOMONOS"
$Shortcut.IconLocation = "d:\Proyectos\EKKOMONOS\assets\icon.ico"
$Shortcut.Save()
Write-Host "Shortcut created at $ShortcutFile"
