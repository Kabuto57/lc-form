// THE BUTTON AND EVENT SCRIPTS. Each section below, after its "// ==== name ====" line, is stored in the PDF
// as one action. The lines before the first marker (this header) are not stored.
//   check-form    the "Check form" button (top right of every page)
//   reset-form    the "Reset form" button (top right of every page)
//   generate-qr   the "Generate QR Code" button (QR page)
//   print-form    the "Print Form" button (QR page)
//   before-save   runs before the form is saved or printed
// They call the functions in document.js (lcRules, lcPayload, lcDrawQr, lcDates).
// ==== check-form ====
// "CHECK FORM" BUTTON: lists what is missing or wrong (at most 15 of each) and puts the cursor on the first
// problem; otherwise says the form is ready.
var m = typeof lcRules == "function" ? lcRules(this) : [], b = m.bad || [], t = [];
function list(a) { return "- " + a.slice(0, 15).join("\n- ") + (a.length > 15 ? "\n- ... and " + (a.length - 15) + " more" : ""); }
if (m.length) t.push(m.length + " mandatory question" + (m.length > 1 ? "s are" : " is") + " still blank:\n" + list(m));
if (b.length) t.push(b.length + " answer" + (b.length > 1 ? "s need" : " needs") + " correcting:\n" + list(b));
if (t.length) { app.alert("This form is not ready to send. The boxes concerned are outlined in red.\n\n" + t.join("\n\n") + "\n\nPlease correct them before you send the form.", 1);
  var g = m.first && this.getField(m.first); if (g) g.setFocus(); }
else app.alert("All mandatory questions are answered and every answer is in the right format. You can save the form and send it.", 3);
// ==== reset-form ====
// "RESET FORM" BUTTON: asks first, then sets every answer back to how the form started, and re-checks.
if (app.alert("Are you sure you want to reset the form? All your answers will be cleared.", 2, 2) == 4) {
this.resetForm(); if (typeof lcDates == "function") lcDates(this); if (typeof lcRules == "function") lcRules(this); }
// ==== generate-qr ====
// "GENERATE QR CODE" BUTTON: refuses while anything is missing or wrong; otherwise makes the QR code from the
// answers (lcPayload, lcDrawQr) and goes to the QR code page.
var m = typeof lcRules == "function" ? lcRules(this) : [], b = m.bad || [], t = [];
function list(a) { return "- " + a.slice(0, 15).join("\n- ") + (a.length > 15 ? "\n- ... and " + (a.length - 15) + " more" : ""); }
if (m.length) t.push(m.length + " mandatory question" + (m.length > 1 ? "s are" : " is") + " still blank:\n" + list(m));
if (b.length) t.push(b.length + " answer" + (b.length > 1 ? "s need" : " needs") + " correcting:\n" + list(b));
if (t.length) { app.alert("The QR code cannot be generated yet. The boxes concerned are outlined in red.\n\n" + t.join("\n\n") + "\n\nPlease correct them, then press Generate QR Code again.", 1);
  var g = m.first && this.getField(m.first); if (g) g.setFocus(); }
else { try { var q = this.getField("__qr"); q.value = lcPayload(this); lcDrawQr(this, q.value); this.pageNum = this.numPages - 1;
  app.alert("The QR code has been generated from your answers (" + q.value.length + " characters). Press Print Form to print the form with the QR code.", 3); }
  catch (e) { app.alert("The QR code could not be generated: " + e + "\nPlease send this message to the form's maintainer.", 1); } }
// ==== print-form ====
// "PRINT FORM" BUTTON: prints only once the QR code exists and still matches the current answers, so the
// printed code always carries the answers on the paper.
var q = this.getField("__qr"), now = typeof lcPayload == "function" ? lcPayload(this) : "", same = false;
try { same = JSON.stringify(JSON.parse(q.value).data) == JSON.stringify(JSON.parse(now).data); } catch (e) {}
if (!/\S/.test(q.value)) app.alert("Please press Generate QR Code first, so the printed form carries the QR code.", 1);
else if (!same) app.alert("Your answers have changed since the QR code was generated. Please press Generate QR Code again, then Print Form.", 1);
else this.print(true, 0, this.numPages - 1, false, true);
// ==== before-save ====
// BEFORE SAVING OR PRINTING: the same list as Check form, shown only if something is missing or wrong.
// It warns but doesn't stop the save or print.
var m = typeof lcRules == "function" ? lcRules(this) : [], b = m.bad || [], t = [];
function list(a) { return "- " + a.slice(0, 15).join("\n- ") + (a.length > 15 ? "\n- ... and " + (a.length - 15) + " more" : ""); }
if (m.length) t.push(m.length + " mandatory question" + (m.length > 1 ? "s are" : " is") + " still blank:\n" + list(m));
if (b.length) t.push(b.length + " answer" + (b.length > 1 ? "s need" : " needs") + " correcting:\n" + list(b));
if (t.length) { app.alert("This form is not ready to send. The boxes concerned are outlined in red.\n\n" + t.join("\n\n") + "\n\nPlease correct them before you send the form.", 1);
   }

