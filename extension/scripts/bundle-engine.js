// Copies the repo's top-level engine/ folder into extension/engine/ so it
// gets bundled into the packaged .vsix. vsce can only package files that
// live inside the extension/ directory, so this runs as a prepackage step
// rather than engine/ permanently living in two places.
//
// engine/ at the repo root remains the single source of truth — this
// script's output (extension/engine/) is a disposable, regenerated-every-
// time copy, and is git-ignored.

const fs = require("fs");
const path = require("path");

const SOURCE = path.join(__dirname, "..", "..", "engine");
const DEST = path.join(__dirname, "..", "engine");

// Never bundle a dev-local virtualenv (huge, platform-specific — the
// packaged extension uses the end user's own system Python instead),
// caches, or anything that might contain secrets.
const EXCLUDED_DIR_NAMES = new Set([
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".git",
]);

const EXCLUDED_FILE_NAMES = new Set([".env"]);

function copyRecursive(src, dest) {
    const stat = fs.statSync(src);

    if (stat.isDirectory()) {
        const dirName = path.basename(src);

        if (EXCLUDED_DIR_NAMES.has(dirName)) {
            return;
        }

        fs.mkdirSync(dest, { recursive: true });

        for (const entry of fs.readdirSync(src)) {
            copyRecursive(path.join(src, entry), path.join(dest, entry));
        }

        return;
    }

    const fileName = path.basename(src);

    if (EXCLUDED_FILE_NAMES.has(fileName) || fileName.endsWith(".pyc")) {
        return;
    }

    fs.copyFileSync(src, dest);
}

if (fs.existsSync(DEST)) {
    fs.rmSync(DEST, { recursive: true, force: true });
}

copyRecursive(SOURCE, DEST);

console.log(`Bundled engine/ -> ${DEST}`);
