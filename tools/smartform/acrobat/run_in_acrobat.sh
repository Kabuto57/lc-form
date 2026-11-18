#!/bin/zsh
# run_in_acrobat.sh file.js: runs the script in Adobe Acrobat (wrapped in try/catch) and prints what it returns.
S=${0:a:h}
{ echo 'var __r; try { __r = (function(){'; cat $1; echo '})(); } catch (e) { __r = "ERR " + e + " line " + e.lineNumber; } __r;'; } > $S/.wrapped.js
osascript -e "with timeout of 900 seconds" -e "tell application \"Adobe Acrobat\" to do script (read POSIX file \"$S/.wrapped.js\" as «class utf8»)" -e "end timeout"
