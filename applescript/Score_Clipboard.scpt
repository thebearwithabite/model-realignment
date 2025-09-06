#!/usr/bin/osascript

(*
Model Realignment: Global Shortcut Handler (v2 - Merged)
- Copies selected text automatically
- Provides clear user notifications
- Logs results to system log
*)

on run
    try
        -- Get the project directory dynamically
        tell application "System Events"
            set scriptFile to file (path to me)
            set scriptsFolder to container of scriptFile
            set projectDir to container of scriptsFolder
            set projectPath to POSIX path of projectDir
        end tell

        -- Store original clipboard
        set originalClipboard to the clipboard
        
        -- Copy currently selected text
        tell application "System Events"
            keystroke "c" using command down
        end tell
        
        delay 0.2
        set copiedText to the clipboard
        
        if copiedText is not originalClipboard then
            display notification "Scoring selected text..." with title "Model Realignment"
            
            set pythonScript to "cd '" & projectPath & "' && /opt/homebrew/bin/python3 main_loop.py --score-text"
            set scoreResult to do shell script "echo " & quoted form of copiedText & " | " & pythonScript
            
            display notification scoreResult with title "Model Realignment" subtitle "Text Scored" sound name "Glass"
            do shell script "echo '[Model Realignment] Score Result: ' & " & quoted form of scoreResult & " | logger -t ModelRealignment"
            
            set the clipboard to originalClipboard
        else
            display notification "No text selected" with title "Model Realignment" subtitle "Selection Required"
        end if
        
    on error errorMessage
        display notification "Error: " & errorMessage with title "Model Realignment" subtitle "Scoring Failed" sound name "Basso"
        do shell script "echo '[Model Realignment ERROR] ' & " & quoted form of errorMessage & " | logger -t ModelRealignment"
    end try
end run
