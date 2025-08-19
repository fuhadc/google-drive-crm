Loop, 1
{
    SetTitleMatchMode, 2
    CoordMode, Mouse, Screen

    tt = Thermal Studio PRO

    ToolTip, Waiting for FLIR window...
    WinWait, %tt%
    ToolTip, FLIR window found

    IfWinNotActive, %tt%
    {
        ToolTip, Activating window...
        WinActivate, %tt%
        WinWaitActive, %tt%, , 2
    }

    Sleep, 648
    ToolTip, Clicking at 904, 308
    MouseClick, L, 904, 308

    Sleep, 429
    ToolTip, Sending Ctrl+A + Delete
    Send, ^a{Delete}

    Sleep, 1000
    ToolTip, Done
    Sleep, 1500
    ToolTip
}
