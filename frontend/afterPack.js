// electron-builder afterPack hook (macOS only; a no-op on every other platform).
//
// We have no Apple Developer certificate, so the app is ad-hoc signed. That still
// matters:
//   * Apple Silicon refuses to run code with no signature at all (the process is
//     killed on launch), and
//   * a downloaded app whose bundle signature doesn't match its contents is
//     reported as "damaged and can't be opened" — a dead end — whereas a validly
//     (ad-hoc) signed one gets the normal "can't verify the developer" prompt that
//     System Settings > Privacy & Security > "Open Anyway" resolves.
//
// So: sign every Mach-O the Python backend ships (PyInstaller's one-folder output
// is an executable plus dozens of .so/.dylib files), then sign the whole .app last
// so its seal covers everything that was just copied into it. The bundled Ollama
// is already signed by Ollama and is deliberately left alone.
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const MACHO_MAGIC = new Set([
  0xfeedface, 0xfeedfacf, 0xcefaedfe, 0xcffaedfe, // thin
  0xcafebabe, 0xbebafeca, // universal
]);

function isMachO(file) {
  let fd;
  try {
    fd = fs.openSync(file, 'r');
    const buffer = Buffer.alloc(4);
    if (fs.readSync(fd, buffer, 0, 4, 0) < 4) return false;
    return MACHO_MAGIC.has(buffer.readUInt32BE(0));
  } catch {
    return false;
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
  }
}

function* walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isSymbolicLink()) continue;
    if (entry.isDirectory()) yield* walk(full);
    else if (entry.isFile()) yield full;
  }
}

function codesign(args) {
  execFileSync('codesign', ['--force', '--sign', '-', '--timestamp=none', ...args], { stdio: 'pipe' });
}

module.exports = async function afterPack(context) {
  if (context.electronPlatformName !== 'darwin') return;

  const appName = context.packager.appInfo.productFilename;
  const appPath = path.join(context.appOutDir, `${appName}.app`);
  const resourcesDir = path.join(appPath, 'Contents', 'Resources');
  const backendDir = path.join(resourcesDir, 'report_generator_backend');
  const backendBinary = path.join(backendDir, 'report_generator_backend');

  // A missing backend would ship an app that can never start: fail the build.
  if (!fs.existsSync(backendBinary)) {
    throw new Error(`[afterPack] backend binary not found at ${backendBinary}`);
  }
  fs.chmodSync(backendBinary, 0o755);

  const ollamaBinary = path.join(resourcesDir, 'ollama', 'ollama');
  if (fs.existsSync(ollamaBinary)) fs.chmodSync(ollamaBinary, 0o755);

  let signed = 0;
  for (const file of walk(backendDir)) {
    if (isMachO(file)) {
      codesign([file]);
      signed += 1;
    }
  }
  console.log(`[afterPack] ad-hoc signed ${signed} backend binaries/libraries`);

  codesign(['--deep', appPath]);
  console.log(`[afterPack] ad-hoc signed ${appPath}`);

  // Fail the build if the seal doesn't hold, rather than ship an app macOS calls "damaged".
  execFileSync('codesign', ['--verify', '--deep', '--verbose=2', appPath], { stdio: 'inherit' });
};
