#!/usr/bin/osascript

(*
Model Realignment: Global Shortcut Handler
Triggered by: Cmd+Shift+S (or custom shortcut)
Flow: Copy selected text → Send to Python scoring engine → Show result
*)

on run
    try
        -- Store original clipboard
        set originalClipboard to the clipboard
        
        -- Copy currently selected text
        tell application "System Events"
            keystroke "c" using command down
        end tell
        
        -- Wait a moment for clipboard to update
        delay 0.2
        
        -- Get the copied text
        set copiedText to the clipboard
        
        -- Only proceed if we actually copied something new
        if copiedText is not originalClipboard then
            -- Call Python scoring engine
            set pythonScript to "cd '/Users/ryanthomson/Github/model-realignment' && /opt/homebrew/bin/python3 main_loop.py --score-text"
            set scoreResult to do shell script "echo " & quoted form of copiedText & " | " & pythonScript
            
            -- Show notification with result
            display notification scoreResult with title "Model Realignment" subtitle "Text Scored"
            
            -- Restore original clipboard
            set the clipboard to originalClipboard
            
        else
            -- No new text copied
            display notification "No text selected" with title "Model Realignment" subtitle "Selection Required"
        end if
        
    on error errorMessage
        -- Handle errors gracefully
        display notification "Error: " & errorMessage with title "Model Realignment" subtitle "Scoring Failed"
    end try
end run

-- Alternative version for direct text input (for testing)
on scoreText(textToScore)
    try
        set pythonScript to "cd '/Users/ryanthomson/Github/model-realignment' && /opt/homebrew/bin/python3 main_loop.py --score-text"
        set scoreResult to do shell script "echo " & quoted form of textToScore & " | " & pythonScript
        return scoreResult
    on error errorMessage
        return "Error: " & errorMessage
    end try
end scoreText