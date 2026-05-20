#!/usr/bin/env node

/**
 * Simple JavaScript minifier for basset-hound frontend
 * Removes comments, whitespace, and compresses variable names
 * Run: node scripts/minify-js.js
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.join(__dirname, '..');
const STATIC_JS_DIR = path.join(PROJECT_ROOT, 'static', 'js');
const DIST_JS_DIR = path.join(PROJECT_ROOT, 'static', 'js', 'dist');

// Ensure dist directory exists
if (!fs.existsSync(DIST_JS_DIR)) {
    fs.mkdirSync(DIST_JS_DIR, { recursive: true });
}

/**
 * Simple minifier that removes comments and unnecessary whitespace
 * This is NOT a full JavaScript minifier, just removes comments and extra whitespace
 */
function minifyJS(code) {
    // Remove single-line comments
    code = code.replace(/\/\/.*?$/gm, '');

    // Remove multi-line comments
    code = code.replace(/\/\*[\s\S]*?\*\//g, '');

    // Remove excessive whitespace (but preserve necessary spaces)
    code = code.replace(/\s+/g, ' ');

    // Remove spaces around operators and brackets
    code = code.replace(/\s*([{};,()[\]=+\-*/:])\s*/g, '$1');

    // Restore necessary spaces after keywords
    code = code.replace(/\b(if|else|for|while|function|return|const|let|var|async|await|import|export|from|as)\b/g, ' $1 ');

    // Clean up excessive spaces
    code = code.replace(/\s+/g, ' ').trim();

    return code;
}

/**
 * Process a single JS file
 */
function minifyFile(filePath, outputPath) {
    try {
        const code = fs.readFileSync(filePath, 'utf8');
        const minified = minifyJS(code);
        fs.writeFileSync(outputPath, minified, 'utf8');

        const originalSize = Buffer.byteLength(code, 'utf8');
        const minifiedSize = Buffer.byteLength(minified, 'utf8');
        const savings = ((1 - minifiedSize / originalSize) * 100).toFixed(2);

        console.log(`✓ ${path.basename(filePath)}: ${originalSize} → ${minifiedSize} bytes (${savings}% savings)`);
        return true;
    } catch (error) {
        console.error(`✗ Error minifying ${filePath}:`, error.message);
        return false;
    }
}

/**
 * Get all JS files in a directory (except dist)
 */
function getJSFiles(dir) {
    return fs.readdirSync(dir)
        .filter(file => file.endsWith('.js') && !file.startsWith('.'))
        .map(file => path.join(dir, file));
}

/**
 * Main execution
 */
async function main() {
    console.log('Starting JavaScript minification...\n');

    const jsFiles = getJSFiles(STATIC_JS_DIR).filter(f => !f.includes('/dist/'));
    let successCount = 0;
    let totalSize = 0;
    let minifiedTotalSize = 0;

    for (const filePath of jsFiles) {
        const fileName = path.basename(filePath);
        const outputPath = path.join(DIST_JS_DIR, fileName);

        const originalSize = Buffer.byteLength(fs.readFileSync(filePath, 'utf8'), 'utf8');
        totalSize += originalSize;

        if (minifyFile(filePath, outputPath)) {
            successCount++;
            minifiedTotalSize += Buffer.byteLength(fs.readFileSync(outputPath, 'utf8'), 'utf8');
        }
    }

    console.log(`\n${successCount}/${jsFiles.length} files minified successfully`);
    console.log(`Total: ${totalSize} → ${minifiedTotalSize} bytes (${((1 - minifiedTotalSize / totalSize) * 100).toFixed(2)}% savings)`);
}

main().catch(console.error);
