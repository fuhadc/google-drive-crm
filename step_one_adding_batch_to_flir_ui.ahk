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

    Sleep, 687
    ToolTip, Clicking at 467, 456
    MouseClick, L, 467, 456

    Sleep, 492
    ToolTip, Clicking at 643, 467
    MouseClick, L, 643, 467

    Sleep, 820
    ToolTip, Moving mouse
    MouseMove, 643, 467

    Sleep, 187
    ToolTip, Sending Ctrl+A
    Send, ^a  ; You don't need {Blind} or {Ctrl Down}{Ctrl Up} for Ctrl+A

    Sleep, 547
    ToolTip, Clicking at 734, 662
    MouseClick, L, 734, 662

    Sleep, 1000
    ToolTip, Done
    Sleep, 1500
    ToolTip
}
