// electron-builder afterPack hook.
//
// On macOS, ad-hoc signs the bundled Python backend binary (built by
// PyInstaller — it ships completely unsigned). Without at least an ad-hoc
// signature, an executable spawned from inside the .app can be refused
// permission to run — this is enforced unconditionally on Apple Silicon.
//
// The bundled Ollama runtime does NOT need this: it ships already signed by
// Ollama itself (verified: the release tarball carries Apple CodeSignature
// extended attributes), so re-signing it here would be redundant.
const { execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');

module.exports = async function afterPack(context) {
  if (context.electronPlatformName !== 'darwin') return;

  const appName = context.packager.appInfo.productFilename;
  const resourcesDir = path.join(context.appOutDir, `${appName}.app`, 'Contents', 'Resources');
  const backendBinary = path.join(resourcesDir, 'report_generator_backend', 'report_generator_backend');

  if (!fs.existsSync(backendBinary)) {
    console.warn(`[afterPack] backend binary not found at ${backendBinary}, skipping ad-hoc signing`);
    return;
  }

  fs.chmodSync(backendBinary, 0o755);
  execFileSync('codesign', ['--force', '--deep', '--sign', '-', backendBinary]);
  console.log(`[afterPack] ad-hoc signed ${backendBinary}`);
};
