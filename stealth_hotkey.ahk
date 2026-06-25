#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%
DetectHiddenWindows, On

WM_USER := 0x0400

F6::
PostMessage, %WM_USER%, 1, 0,, StealthPlayerWindow
return

Insert::
PostMessage, %WM_USER%, 2, 0,, StealthPlayerWindow
return

!q::
PostMessage, %WM_USER%, 3, 0,, StealthPlayerWindow
return