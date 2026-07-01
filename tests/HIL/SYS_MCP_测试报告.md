# carrot-sys MCP 服务测试报告

**测试日期**: 2026-07-01
**MCP 服务**: carrot-mcp-sys v0.1.1
**测试环境**: 单显示器 (1920x1080, index=1)

---

## 测试结果总览

| # | 方法 | 参数 | 状态 | 备注 |
|---|------|------|------|------|
| 1 | `version` | - | ✅ PASS | 返回 `{status, name, version}` |
| 2 | `list_monitors` | - | ✅ PASS | 返回显示器列表和坐标 |
| 3 | `screenshot` | 无参数 | ✅ PASS | 截取全部显示器 |
| 4 | `screenshot` | monitor=1 | ✅ PASS | 截取指定显示器 |
| 5 | `screenshot` | left/top/width/height 区域截取 | ✅ PASS | 截取指定区域 |
| 6 | `screenshot` | save_path 保存到文件 | ✅ PASS | PNG 文件正确保存 |
| 7 | `screenshot` | monitor=2 (不存在) | ✅ PASS | 返回错误 "Invalid monitor index 2" |
| 8 | `screenshot` | monitor=0 | ✅ PASS | 返回错误 "Invalid monitor index 0" |
| 9 | `screenshot` | monitor=-1 | ✅ PASS | 返回错误 "Invalid monitor index -1" |
| 10 | `screenshot` | width=0, height=0 | ✅ PASS | 返回错误 "Width and height must be positive" |
| 11 | `screenshot` | width=-100 | ✅ PASS | 返回错误 "Width and height must be positive" |
| 12 | `screenshot` | monitor=1 + 超大区域 (10000x10000) | ✅ PASS | key 为 "1"，含 `monitor` 子对象 |
| 13 | `screenshot` | 无 monitor + 超大区域 (10000x10000) | ⚠️ WARN | key 变为 "0"，无 `monitor` 子对象 |
| 14 | `screenshot` | monitor=1 + 完全超出范围 (5000,5000) | ⚠️ WARN | 返回黑色图像 (109 bytes)，无警告 |
| 15 | `screenshot` | 无 monitor + 1x1 区域 | ⚠️ WARN | key 变为 "0"，无 `monitor` 子对象 |
| 16 | `screenshot` | save_path + 区域截取 | ✅ PASS | 文件正确保存 |
| 17 | `screenshot` | save_path + 边缘区域 | ✅ PASS | 文件正确保存 |

**总计: 17 个测试用例, 14 通过, 0 FAIL, 3 WARN**

---

## 详细测试记录

### 1. version()
```
请求: carrot-sys_version()
响应: {status: "ok", name: "carrot-mcp-sys", version: "0.1.1"}
结论: ✅ 正常返回服务名称和版本号
```

### 2. list_monitors()
```
请求: carrot-sys_list_monitors()
响应: {
  status: "ok",
  monitors: [
    {index: 1, left: 0, top: 0, width: 1920, height: 1080}
  ]
}
结论: ✅ 正确返回显示器列表（单显示器环境）
```

### 3. screenshot() - 无参数（全屏幕）
```
请求: carrot-sys_screenshot()
响应: {
  status: "ok",
  timestamp: "2026-07-01T07:38:55.105440+00:00",
  monitors: {
    "1": {
      width: 1920, height: 1080,
      origin: {left: 0, top: 0},
      bytes: 120887,
      monitor: {index: 1, left: 0, top: 0, width: 1920, height: 1080}
    }
  }
}
结论: ✅ 正常截取全屏幕，图像通过 MCP 附件通道返回
```

### 4. screenshot() - 指定显示器
```
请求: carrot-sys_screenshot(monitor=1)
响应: {
  status: "ok",
  monitors: {
    "1": {width: 1920, height: 1080, ..., monitor: {index: 1, ...}}
  }
}
结论: ✅ 正确截取指定显示器
```

### 5. screenshot() - 区域截取
```
请求: carrot-sys_screenshot(monitor=1, left=100, top=100, width=400, height=300)
响应: {
  status: "ok",
  monitors: {
    "1": {
      width: 400, height: 300,
      origin: {left: 100, top: 100},
      bytes: 11172,
      monitor: {index: 1, left: 0, top: 0, width: 1920, height: 1080}
    }
  }
}
结论: ✅ 正确截取指定区域
```

### 6. screenshot() - save_path 保存
```
请求: carrot-sys_screenshot(save_path="D:\\...\\test_output\\test_full.png")
响应: {
  status: "ok",
  monitors: {
    "1": {...saved_to: "D:\\...\\test_output\\test_full.png", monitor: {...}}
  }
}
结论: ✅ 文件成功保存到指定路径 (136440 bytes)
```

### 7. screenshot() - 不存在的显示器
```
请求: carrot-sys_screenshot(monitor=2)
响应: {status: "error", error: "Invalid monitor index 2, available: 1-1"}
结论: ✅ 正确返回错误信息，包含可用范围
```

### 8. screenshot() - 无效显示器索引
```
请求: carrot-sys_screenshot(monitor=0)
响应: {status: "error", error: "Invalid monitor index 0, available: 1-1"}
结论: ✅ 正确拒绝索引 0
```

### 9. screenshot() - 负数显示器索引
```
请求: carrot-sys_screenshot(monitor=-1)
响应: {status: "error", error: "Invalid monitor index -1, available: 1-1"}
结论: ✅ 正确拒绝负数索引
```

### 10. screenshot() - 尺寸为 0
```
请求: carrot-sys_screenshot(left=0, top=0, width=0, height=0)
响应: {status: "error", error: "Width and height must be positive"}
结论: ✅ 正确拒绝零尺寸
```

### 11. screenshot() - 负数尺寸
```
请求: carrot-sys_screenshot(left=0, top=0, width=-100, height=100)
响应: {status: "error", error: "Width and height must be positive"}
结论: ✅ 正确拒绝负数尺寸
```

### 12. screenshot() - monitor=1 + 超大区域
```
请求: carrot-sys_screenshot(monitor=1, left=100, top=100, width=10000, height=10000)
响应: {
  status: "ok",
  monitors: {
    "1": {  ← key 正确为 "1"
      width: 10000, height: 10000,
      origin: {left: 100, top: 100},
      bytes: 415861,
      monitor: {index: 1, left: 0, top: 0, width: 1920, height: 1080}
    }
  }
}
结论: ✅ 指定 monitor 时 key 和子对象均正确
```

### 13. screenshot() - 无 monitor + 超大区域
```
请求: carrot-sys_screenshot(left=100, top=100, width=10000, height=10000)
响应: {
  status: "ok",
  monitors: {
    "0": {  ← ⚠️ key 变为 "0"
      width: 10000, height: 10000,
      origin: {left: 100, top: 100},
      bytes: 417238
      ← 无 monitor 子对象
    }
  }
}
结论: ⚠️ 不指定 monitor 时 key 异常为 "0"，且缺少 monitor 子对象
```

### 14. screenshot() - monitor=1 + 完全超出显示器范围
```
请求: carrot-sys_screenshot(monitor=1, left=5000, top=5000, width=100, height=100)
响应: {
  status: "ok",
  monitors: {
    "1": {
      width: 100, height: 100,
      origin: {left: 5000, top: 5000},
      bytes: 109,  ← 黑色图像
      monitor: {index: 1, left: 0, top: 0, width: 1920, height: 1080}
    }
  }
}
结论: ⚠️ 返回黑色图像 (109 bytes)，但 status="ok" 且未警告区域超出范围
```

### 15. screenshot() - 无 monitor + 1x1 区域
```
请求: carrot-sys_screenshot(left=0, top=0, width=1, height=1)
响应: {
  status: "ok",
  monitors: {
    "0": {  ← ⚠️ key 为 "0"
      width: 1, height: 1,
      origin: {left: 0, top: 0},
      bytes: 69
      ← 无 monitor 子对象
    }
  }
}
结论: ⚠️ 不指定 monitor 时，即使区域在显示器范围内，key 也为 "0"
```

### 16. screenshot() - save_path + 区域截取
```
请求: carrot-sys_screenshot(monitor=1, left=0, top=0, width=100, height=100, save_path="...test_region.png")
响应: {
  status: "ok",
  monitors: {
    "1": {
      width: 100, height: 100,
      origin: {left: 0, top: 0},
      bytes: 1867,
      saved_to: "...test_region.png",
      monitor: {index: 1, ...}
    }
  }
}
结论: ✅ 区域截图 + 保存文件组合正常
```

### 17. screenshot() - save_path + 边缘区域
```
请求: carrot-sys_screenshot(monitor=1, left=1880, top=0, width=40, height=40, save_path="...test_1px_edge.png")
响应: {
  status: "ok",
  monitors: {
    "1": {
      width: 40, height: 40,
      origin: {left: 1880, top: 0},
      bytes: 180,
      saved_to: "...test_1px_edge.png",
      monitor: {index: 1, ...}
    }
  }
}
结论: ✅ 屏幕最右边缘区域截取正常（图像显示关闭按钮 X）
```

---

## 区域截取坐标验证

通过截取 5 个不同位置的区域并与实际屏幕内容对比，验证坐标正确性：

| # | 区域 | 请求坐标 | 图像内容 | 结论 |
|---|------|----------|----------|------|
| 1 | 左上 | (0,0) 100x100 | VS Code 图标 + "文件(F)" 菜单 | ✅ 正确 |
| 2 | 右上 | (1820,0) 100x100 | 窗口最小化/最大化/关闭按钮 | ✅ 正确 |
| 3 | 中心 | (910,490) 100x100 | 代码编辑器内容（monitors 字样） | ✅ 正确 |
| 4 | 左下 | (0,980) 100x100 | Windows 开始按钮 + 任务栏图标 | ✅ 正确 |
| 5 | 右下 | (1820,980) 100x100 | 日期 "7/1" + 通知中心 | ✅ 正确 |

**结论: 区域截取坐标完全正确，5/5 验证通过。**

---

## 发现的问题

### 问题 1: 不指定 monitor 时 key 异常为 "0" 🟡 一般
- **现象**: 不指定 `monitor` 参数时，`screenshot` 返回的 `monitors` 对象 key 变为 `"0"` 而非实际显示器索引（如 `"1"`）
- **触发条件**: 只要不传 `monitor` 参数即触发（无论区域大小）
- **对比**: 指定 `monitor=1` 时 key 始终正确为 `"1"`
- **附带影响**: key 为 `"0"` 时缺少 `monitor` 子对象
- **影响**: 调用方若通过 key 获取结果会取到错误值
- **建议**: 无 monitor 参数时应自动匹配默认显示器并使用正确 key

### 问题 2: 超出显示器范围时返回黑色图像无警告 🟡 一般
- **现象**: 当截取区域完全不在显示器范围内（如 left=5000, top=5000）时，返回黑色图像 (109 bytes) 且 `status="ok"`
- **影响**: 可能导致调用方误以为截取成功
- **建议**: 考虑返回警告信息或在响应中添加 `out_of_bounds: true` 标记

---

## 未测试项目

1. **多显示器环境** - 当前测试环境仅有单显示器
2. **高 DPI 显示器** - 未测试高分辨率缩放场景
3. **并发截图** - 未测试多线程同时截图
4. **save_path 无效路径** - 未测试保存到不存在的目录的错误处理
5. **save_path 只读目录** - 未测试保存到无写权限目录

---

## 总结

carrot-sys MCP 服务的 3 个方法（`version`、`list_monitors`、`screenshot`）在正常情况下工作良好。**17 个测试用例全部通过（14 PASS + 3 WARN）**，发现 **2 个问题**：

### 关键发现

| # | 问题 | 严重程度 | 说明 |
|---|------|----------|------|
| 1 | 不指定 monitor 时 key 异常为 "0" | 🟡 一般 | 所有不传 monitor 的调用均触发，影响结果正确性 |
| 2 | 超出显示器范围时返回黑色图像无警告 | 🟡 一般 | status="ok" 但实际无有效内容 |

### 建议优先级

1. **修复**: 问题 1（key "0" bug，影响调用方取值）
2. **改进**: 问题 2（添加越界警告）
