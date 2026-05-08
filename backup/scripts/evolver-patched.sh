#!/data/data/com.termux/files/usr/bin/bash
# Wrapper that patches os.loadavg/cpus before running evolver
node -e "
// Patch os module BEFORE evolver loads
const os = require('os');
os.loadavg = () => [0.2, 0.2, 0.2];
os.cpus = () => Array(4).fill({
  model: 'ARM Cortex', speed: 2400,
  times: { user: 0, nice: 0, sys: 0, idle: 100, irq: 0 }
});

// Patch os in the Module prototype chain so any require('os') gets our version
const Module = require('module');
const originalLoad = Module._load;
Module._load = function(name, parent) {
  if (name === 'os') {
    return os;
  }
  return originalLoad.apply(this, arguments);
};

process.argv = ['node', 'evolver-patched.js', 'run'];
require('child_process').execSync('node evolver-patched.js', { cwd: require('path').dirname(require.resolve('@evomap/evolver')), stdio: 'inherit' });
"
