#!/usr/bin/env node
// Cross-platform dispatcher for the backend build step, invoked from
// frontend/package.json's "preelectron:build" script. Runs build_exe.ps1 on
// Windows (unchanged behavior) or build_exe.sh on macOS/Linux.
const { spawnSync } = require('child_process');
const path = require('path');

const isWindows = process.platform === 'win32';
const scriptPath = path.join(__dirname, isWindows ? 'build_exe.ps1' : 'build_exe.sh');

const result = isWindows
  ? spawnSync('powershell', ['-ExecutionPolicy', 'Bypass', '-File', scriptPath], { stdio: 'inherit' })
  : spawnSync('bash', [scriptPath], { stdio: 'inherit' });

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status === null ? 1 : result.status);
