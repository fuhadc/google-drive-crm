Loop, 1
{
    SetTitleMatchMode, 2
    CoordMode, Mouse, Screen

    ; Use simpler and more reliable title matching
    tt = Thermal Studio PRO

    ToolTip, Waiting for FLIR window...
    WinWait, %tt%
    ToolTip, FLIR window found

    ; Make sure the window is active
    IfWinNotActive, %tt%
    {
        ToolTip, Activating window...
        WinActivate, %tt%
        WinWaitActive, %tt%, , 2
    }

    Sleep, 1257
    ToolTip, Clicking at 1158, 102
    MouseClick, L, 1158, 102

    Sleep, 1000
    ToolTip, Done
    Sleep, 1500
    ToolTip
}
