import { createHash } from "node:crypto";
import { closeSync, openSync, readSync } from "node:fs";

const CHUNK = 1024 * 1024;
const digest = createHash("sha256");
const buf = Buffer.allocUnsafe(CHUNK);
const fd = openSync(process.argv[2], "r");
let n: number;
while ((n = readSync(fd, buf, 0, CHUNK, null)) > 0) digest.update(buf.subarray(0, n));
closeSync(fd);
console.log(digest.digest("hex"));
