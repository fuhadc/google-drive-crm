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

    Sleep, 789
    ToolTip, Clicking at 1298, 700
    MouseClick, L, 1298, 700

    Sleep, 1000
    ToolTip, Done
    Sleep, 1500
    ToolTip
}
