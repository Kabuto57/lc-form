// Builds the LC application PDF:  npm run build  ->  out/LC-Application.pdf
import { mkdirSync, writeFileSync } from "node:fs";
import { buildPdf } from "./src/form/build.ts";
import { LC } from "./src/lc.ts";

mkdirSync("out", { recursive: true });
writeFileSync("out/LC-Application.pdf", await buildPdf(LC.template, LC.defaults, "javascript"));
console.log("Wrote out/LC-Application.pdf");
