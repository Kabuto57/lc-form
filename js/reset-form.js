// "RESET FORM" BUTTON: asks first, then sets every answer back to how the form started, and re-checks.
if (app.alert("Are you sure you want to reset the form? All your answers will be cleared.", 2, 2) == 4) {
this.resetForm(); if (typeof lcDates == "function") lcDates(this); if (typeof lcRules == "function") lcRules(this); }