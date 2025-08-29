#!/usr/bin/osascript

-- Model Realignment: Show Status
-- Global shortcut: Cmd+Option+R (for Realignment)
-- Shows current system status

on run
	try
		-- Run the status command
		set scriptPath to "/Users/ryanthomson/Github/model-realignment/main_loop.py"
		set command to "python3 " & quoted form of scriptPath & " --status"
		
		set jsonResult to do shell script command
		
		-- Parse basic info from JSON (simplified)
		set statusDialog to "Model Realignment Status\n\n"
		
		-- Show full JSON in a dialog
		display dialog statusDialog & jsonResult buttons {"Copy to Clipboard", "OK"} default button "OK" with title "Model Realignment Status"
		
		set dialogResult to result
		
		-- If user clicked "Copy to Clipboard"
		if button returned of dialogResult is "Copy to Clipboard" then
			set the clipboard to jsonResult
			display notification "Status copied to clipboard" with title "Model Realignment"
		end if
		
	on error errorMessage
		display notification "Error getting status: " & errorMessage with title "Model Realignment Error" sound name "Basso"
		
		-- Log error
		do shell script "echo '[Model Realignment ERROR] Status error: " & errorMessage & "' | logger -t ModelRealignment"
	end try
end run