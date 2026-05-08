#!/data/data/com.termux/files/usr/bin/env node
// evolver-launch.js — patches os.loadavg/cpus before evolver runs
// This bypasses the system load check on Android Termux where os.cpus() returns 0

const Module = require('module');
const originalLoad = Module._load;

// Create patched os module
const os = require('os');
os.loadavg = () => [0.15, 0.15, 0.15];
os.cpus = () => Array(4).fill({
  model: 'ARM Cortex-A78',
  speed: 2400,
  times: { user: 0, nice: 0, sys: 0, idle: 100, irq: 0 }
});

// Intercept all require('os') calls
Module._load = function(name, parent) {
  if (name === 'os') {
    return os;
  }
  return originalLoad.apply(this, arguments);
};

// Now load and run evolver with the provided args
const path = require('path');
const evolverMain = '/data/data/com.termux/files/usr/lib/node_modules/@evomap/evolver/index.js';

process.argv = ['node', 'evolver', ...process.argv.slice(2)];
require(evolverMain);
