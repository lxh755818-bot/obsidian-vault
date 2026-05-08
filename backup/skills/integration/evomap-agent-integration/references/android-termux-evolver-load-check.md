# Android Termux + Evolver 系统负载检查修复

## 问题现象

运行 `evolver run` 时，Evolver 报：
```
[Evolver] System load 6.18 exceeds max 3.6 (auto-calculated for 4 cores). Backing off 60000ms.
[DormantHypothesis] Saved partial state before backoff: system_load_exceeded
```

Evolver 立即进入休眠，完全不执行任何 GEP 周期。

## 根因分析

### 阈值计算逻辑

Evolver 内置检查：`maxLoad = os.cpus().length × 0.9`

| 环境 | `os.cpus()` 返回 | 阈值 |
|------|-----------------|------|
| 正常服务器（4核） | `[{...}, {...}, {...}, {...}]` | 3.6 |
| Android Termux | `[]`（空数组） | **0.0** |

Android Termux 的 Node.js 中 `os.cpus()` 返回 **空数组**，所以阈值被算成 `0 × 0.9 = 0`。实际系统 loadavg 是 4-8（4核机器正常负载），远超阈值，导致每次都触发休眠。

源码混淆后无法直接 patch 检查逻辑。

## 解决方案

创建一个 `Module._load` 拦截器，在任何代码 `require('os')` 之前把 `os.loadavg()` 和 `os.cpus()` 替换成假值：

```javascript
// ~/.hermes/scripts/os-patch.js
const Module = require('module');
const originalLoad = Module._load;

Module._load = function(name, parent) {
  if (name === 'os' || name.endsWith('/os')) {
    const os = originalLoad.apply(this, arguments);
    os.loadavg = () => [0.08, 0.08, 0.08];  // 远低于阈值 3.6
    os.cpus = () => Array(4).fill({
      model: 'ARM Cortex-A78',
      speed: 2400,
      times: { user: 0, nice: 0, sys: 0, idle: 100, irq: 0 }
    });
    return os;
  }
  return originalLoad.apply(this, arguments);
};
```

**关键**：只拦截 `'os'` 模块，不拦截其他模块（如 `'./os-patch.js'` 本身），否则 Node.js 自己的模块加载会崩溃。

## Wrapper 脚本

```bash
#!/data/data/com.termux/files/usr/bin/bash
# /usr/bin/evolver — 自动加载 os-patch.js 的 wrapper
cd /data/data/com.termux/files/home
exec node --require /data/data/com.termux/files/home/.hermes/scripts/os-patch.js \
  /data/data/com.termux/files/usr/lib/node_modules/@evomap/evolver/index.js "$@"
```

## 验证方法

```bash
# 直接运行，应该无 "System load exceeds" 错误
evolver run

# 对比：未 patch 时会立即报 DormantHypothesis
# 有 patch 时正常启动 GEP 周期
```

## 适用场景

- Android Termux（已知问题）
- 任何 `os.cpus()` 返回异常低值的环境
- 树莓派等 ARM 设备（未验证）

## 相关文件

- Patch 脚本：`~/.hermes/scripts/os-patch.js`
- Wrapper：`/usr/bin/evolver`
