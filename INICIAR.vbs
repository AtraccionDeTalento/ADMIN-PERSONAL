' ═══════════════════════════════════════════════════════════════════════
'  INICIAR.vbs  —  Sistema DJ Quinta Categoria
'  Doble clic para arrancar. Si falla, ejecuta INSTALAR.bat primero.
' ═══════════════════════════════════════════════════════════════════════
Option Explicit

Dim fso, shell, dir, pyExe, pyScript, installBat, rc

Set fso   = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

dir      = fso.GetParentFolderName(WScript.ScriptFullName)
pyExe    = dir & "\venv\Scripts\pythonw.exe"
pyScript = dir & "\servidor_dj_quinta.py"
installBat = dir & "\INSTALAR.bat"
updateBat = dir & "\ACTUALIZAR.bat"

' Si no hay venv, autorreparar ejecutando instalador
If Not fso.FileExists(pyExe) Then
    If Not fso.FileExists(installBat) Then
        MsgBox "No se encontro INSTALAR.bat en esta carpeta." & vbCrLf & _
               "No se puede reparar la instalacion automaticamente.", _
               vbCritical, "Instalador no encontrado"
        WScript.Quit 1
    End If

    rc = MsgBox("No se detecto el entorno virtual." & vbCrLf & vbCrLf & _
                "Quieres ejecutar INSTALAR.bat ahora para dejar todo listo?", _
                vbQuestion + vbYesNo, "Reparacion automatica")
    If rc = vbYes Then
        shell.CurrentDirectory = dir
        shell.Run "cmd /c """ & installBat & """", 1, True
    Else
        WScript.Quit 1
    End If

    If Not fso.FileExists(pyExe) Then
        MsgBox "La instalacion no termino correctamente." & vbCrLf & _
               "Ejecuta INSTALAR.bat nuevamente y espera hasta el final.", _
               vbExclamation, "Instalacion incompleta"
        WScript.Quit 1
    End If
End If

' Si pythonw falla, intentar reparar automaticamente
rc = shell.Run("cmd /c """"" & pyExe & """"" --version >nul 2>&1", 0, True)
If rc <> 0 Then
    If fso.FileExists(installBat) Then
        shell.CurrentDirectory = dir
        shell.Run "cmd /c """ & installBat & """", 1, True
        rc = shell.Run("cmd /c """"" & pyExe & """"" --version >nul 2>&1", 0, True)
    End If
End If

If rc <> 0 Then
    MsgBox "El entorno virtual sigue fallando despues de la reparacion." & vbCrLf & _
           "Revisa el resultado de INSTALAR.bat.", _
           vbCritical, "No se pudo iniciar"
    WScript.Quit 1
End If

' ----------------------------------------------------
' ACTUALIZACIÓN AUTOMÁTICA
' ----------------------------------------------------
If fso.FileExists(updateBat) Then
    shell.CurrentDirectory = dir
    ' Ejecutar ACTUALIZAR.bat y esperar a que termine (1 = ventana visible, True = esperar)
    shell.Run """" & updateBat & """", 1, True
End If
' ----------------------------------------------------

' Liberar puerto 5010 si esta ocupado
shell.Run "cmd /c for /f ""tokens=5"" %a in ('netstat -ano ^| findstr :5010 ^| findstr LISTEN') do taskkill /F /PID %a 2>nul", 0, True

' Iniciar servidor (ventana oculta, asincrono)
shell.CurrentDirectory = dir
shell.Run """" & pyExe & """ """ & pyScript & """", 0, False

' Abrir navegador tras dar tiempo al servidor para arrancar
WScript.Sleep 3000
shell.Run "http://localhost:5010", 1, False

Set fso   = Nothing
Set shell = Nothing
