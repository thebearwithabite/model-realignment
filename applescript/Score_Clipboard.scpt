#!/usr/bin/osascript

-- Model Realignment: Score Clipboard Text
-- Global shortcut: Cmd+Option+S
-- Scores clipboard content using the Model Realignment system

on run
	try
		-- Get clipboard content
		set clipboardText to (the clipboard as string)
		
		-- Check if clipboard has content
		if clipboardText is "" then
			display notification "Clipboard is empty" with title "Model Realignment"
			return
		end if
		
		-- Show notification that scoring is starting
		display notification "Scoring clipboard content..." with title "Model Realignment"
		
		-- Run the scoring command
		set scriptPath to "/Users/ryanthomson/Github/model-realignment/main_loop.py"
		set command to "echo " & quoted form of clipboardText & " | python3 " & quoted form of scriptPath & " --score-text"
		
		set result to do shell script command
		
		-- Show result notification
		display notification result with title "Model Realignment" sound name "Glass"
		
		-- Also log to system log
		do shell script "echo '[Model Realignment] " & result & "' | logger -t ModelRealignment"
		
	on error errorMessage
		-- Show error notification
		display notification "Error: " & errorMessage with title "Model Realignment Error" sound name "Basso"
		
		-- Log error
		do shell script "echo '[Model Realignment ERROR] " & errorMessage & "' | logger -t ModelRealignment"
	end try
end run