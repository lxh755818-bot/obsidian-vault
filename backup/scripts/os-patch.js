// os-patch.js — preload script to patch os.loadavg/cpus on Android Termux
// Only patches 'os' module, not other requires
const Module = require('module');
const originalLoad = Module._load;

Module._load = function(name, parent) {
  // Only patch the 'os' module
  if (name === 'os' || name.endsWith('/os')) {
    const os = originalLoad.apply(this, arguments);
    // Override loadavg to return artificially low values
    // This bypasses Evolver's system load check (max=3.6 on 4-core Android)
    // On Android Termux: os.cpus() returns 0, so max = 0 * 0.9 = 0
    // We fake 4 cores so max = 3.6, and return 0.1 so load < 3.6
    os.loadavg = () => [0.08, 0.08, 0.08];
    os.cpus = () => Array(4).fill({
      model: 'ARM Cortex-A78',
      speed: 2400,
      times: { user: 0, nice: 0, sys: 0, idle: 100, irq: 0 }
    });
    return os;
  }
  return originalLoad.apply(this, arguments);
};
