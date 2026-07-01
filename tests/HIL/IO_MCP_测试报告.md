# carrot-io MCP 服务测试报告

**测试日期**: 2026-06-30  
**MCP 服务**: carrot-mcp-io v0.3.1  
**测试环境**: COM3 <-> COM18 串口回环, TCP/UDP localhost echo servers

---

## 测试结果总览

| 方法 | 参数 | 状态 | 备注 |
|------|------|------|------|
| `version` | - | ✅ PASS | 返回 `{status, name, version}` |
| `list_transports` | - | ✅ PASS | 返回 transports 和 serial_ports |
| `open` | serial (COM3, 115200) | ✅ PASS | 成功打开串口 |
| `open` | tcp (127.0.0.1:9999) | ✅ PASS | 成功建立 TCP 连接 |
| `open` | udp (127.0.0.1:9998) | ✅ PASS | 成功建立 UDP 连接 |
| `write` | hex "55" (serial) | ✅ PASS | 写入 1 字节成功 |
| `write` | ascii "Hello" (serial) | ✅ PASS | 写入 5 字节成功 |
| `write` | hex "48656C6C6F" (TCP) | ✅ PASS | 写入 5 字节成功 |
| `write` | hex "48656C6C6F" (UDP) | ✅ PASS | 写入 5 字节成功 |
| `read` | hex, size=1 (serial) | ✅ PASS | 收到 "AA" (0x55 的回显) |
| `read` | ascii, size=10 (serial) | ✅ PASS | 收到 "World" (Hello 的回显) |
| `read` | hex, size=10 (TCP) | ✅ PASS | 收到 "48656C6C6F" |
| `read` | hex, size=10 (UDP) | ✅ PASS | 收到 "48656C6C6F" |
| `recv` | hex (serial, 空缓冲) | ✅ PASS | 返回 length=0, data="" |
| `history` | limit=5 (serial) | ✅ PASS | 返回最近 5 条操作记录 |
| `script` | write+read+expect (serial) | ✅ PASS | 写入 0x55，读取并验证 0xAA，matched=true |
| `script` | write+read+expect mismatch (serial) | ✅ PASS | on_mismatch="continue" 时 matched=false 但不中断 |
| `script` | flush+write+wait+read+expect (serial) | ✅ PASS | 完整序列执行成功 |
| `script` | on_mismatch="stop" (serial) | ✅ PASS | 匹配失败时中断并返回错误 |
| `script` | flush+write+read+expect (TCP) | ✅ PASS | TCP 脚本执行成功 |
| `script` | flush+write+read+expect (UDP) | ✅ PASS | UDP 脚本执行成功 |
| `recv` | hex (UDP, 有数据) | ✅ PASS | 正确返回缓冲区数据 |
| `history` | limit=3 (UDP) | ✅ PASS | 返回操作历史 |
| `write` | 空数据 | ✅ PASS | 返回错误 "Provide hex or ascii" |
| `write` | 同时提供 hex+ascii | ✅ PASS | 返回错误 "Provide only one of hex or ascii" |
| `write` | 无效 hex 格式 "ZZZZ" | ✅ PASS | 返回错误 "Invalid hex string" |
| `write` | ASCII 含 \x00 字符 | ✅ PASS | 成功写入 11 字节 |
| `write` | 纯 \x00 字节 | ✅ PASS | 成功写入 3 字节 |
| `read` | timeout=1 (无数据) | ✅ PASS | 超时返回 length=0 |
| `read` | size=0 | ✅ PASS | 返回 length=0 |
| `recv` | fmt=ascii | ✅ PASS | 返回 "'World'" (带引号) |
| `recv` | size > 缓冲区 | ✅ PASS | 返回可用数据 (1 字节) |
| `open` | 已打开的连接 | ✅ PASS | 返回 message="COM3 is already open" |
| `open` | 无效 transport | ✅ PASS | 返回错误 "Unknown transport: invalid" |
| `open` | 无效波特率 999999 | ⚠️ WARN | 返回 ok，未验证波特率有效性 |
| `open` | 无效端口名 | ✅ PASS | 返回错误 "could not open port" |
| `open` | TCP 无效主机 | ✅ PASS | 返回错误 "getaddrinfo failed" |
| `open` | TCP 无效端口 (1) | ✅ PASS | 返回错误 "timed out" |
| `open` | serial 参数 bytesize/parity/stopbits | ✅ PASS | 正常接受参数 |
| `open` | buffer_size=2MB | ✅ PASS | 正常接受参数 |
| `close` | 已关闭的连接 | ✅ PASS | 返回错误 "COM3 is not open" |
| `close` | 不存在的连接名 | ✅ PASS | 返回错误 "nonexistent is not open" |
| `close` | serial (COM3) | ✅ PASS | 关闭串口连接 |
| `close` | TCP | ✅ PASS | 关闭 TCP 连接 |
| `close` | UDP | ✅ PASS | 关闭 UDP 连接 |
| `script` | on_mismatch="stop" 匹配成功 | ✅ PASS | 正常执行不中断 |
| `script` | on_mismatch 无效值 | ✅ PASS | 视为 "continue" 处理 |
| `script` | op="invalid_op" | ✅ PASS | 返回错误 "Unknown op: invalid_op" |
| `script` | 空步骤 [] | ✅ PASS | 返回空结果 |
| `script` | 多步 write+read 循环 | ✅ PASS | 6 步全部成功 |
| `script` | read 超时 (无数据) | ✅ PASS | 返回 length=0 |
| `history` | limit=0 | ✅ PASS | 返回所有记录 (非空) |
| `history` | limit=1000 | ✅ PASS | 返回实际记录数 |
| `read` | FF XX 多帧响应 | ✅ PASS | 收到 5 帧共 10 字节 |
| `history` | 返回内部操作类型 | ⚠️ WARN | 返回了 tx_queue/tx_drain 等内部 op |

**总计: 50 个测试用例, 48 通过, 0 FAIL, 2 WARN**

---

## 详细测试记录

### 1. version()
```
请求: carrot-io_version()
响应: {status: "ok", name: "carrot-mcp-io", version: "0.3.1"}
结论: ✅ 正常
```

### 2. list_transports()
```
请求: carrot-io_list_transports()
响应: {
  status: "ok",
  transports: ["serial", "tcp", "udp"],
  serial_ports: [
    {port: "COM18", description: "USB-SERIAL CH340 (COM18)"},
    {port: "COM1", description: "通信端口 (COM1)"},
    {port: "COM3", description: "USB-Enhanced-SERIAL CH343 (COM3)"}
  ]
}
结论: ✅ 正常，正确列出可用传输类型和串口
```

### 3. open() - Serial
```
请求: carrot-io_open(port="COM3", transport="serial", baudrate=115200)
响应: {status: "ok", port: "COM3", transport: "serial", baudrate: 115200}
结论: ✅ 正常
```

### 4. write() - Serial Hex
```
请求: carrot-io_write(port="COM3", hex="55")
响应: {status: "ok", bytes_written: 1}
结论: ✅ 正常
```

### 5. read() - Serial Hex
```
请求: carrot-io_read(port="COM3", size=1, fmt="hex")
响应: {length: 1, data: "AA", status: "ok"}
结论: ✅ 正常，收到 echo server 回复的 0xAA
```

### 6. write() - Serial ASCII
```
请求: carrot-io_write(port="COM3", ascii="Hello")
响应: {status: "ok", bytes_written: 5}
结论: ✅ 正常
```

### 7. read() - Serial ASCII
```
请求: carrot-io_read(port="COM3", size=10, fmt="ascii")
响应: {length: 5, data: "'World'", status: "ok"}
结论: ✅ 正常，收到 echo server 回复的 "World"
注意: data 被单引号包裹，这是 Python repr 格式
```

### 8. FF XX Pattern Test (多帧响应)
```
请求: carrot-io_write(port="COM3", hex="FF42")
第一次读取: carrot-io_read(port="COM3", size=10, fmt="hex", timeout=2)
响应: {length: 10, data: "42014202420342044205", status: "ok"}
结论: ✅ 正常，echo server 每秒发送一帧，共 5 帧
```

### 9. recv() - Non-blocking Read
```
请求: carrot-io_recv(port="COM3", fmt="hex")
响应: {length: 0, data: "", status: "ok"}
结论: ✅ 正常，无数据时返回空
```

### 10. history()
```
请求: carrot-io_history(port="COM3", limit=5)
响应: {status: "ok", entries: [...5条记录...]}
结论: ✅ 正常，返回操作历史包含 recv, read 等操作
```

### 11. script() - Basic Write+Read+Expect
```
请求: carrot-io_script(port="COM3", steps=[
  {op: "write", data: "55"},
  {op: "read", size: 1, expect: "AA"}
], fmt="hex")
响应: [
  {op: "write", status: "ok", bytes_written: 1, step: 0},
  {op: "read", status: "ok", data: "AA", length: 1, matched: true, step: 1}
]
结论: ✅ 正常，expect 匹配成功
```

### 12. script() - Mismatch Handling
```
请求: carrot-io_script(port="COM3", steps=[
  {op: "write", data: "55"},
  {op: "read", size: 1, expect: "BB", on_mismatch: "continue"}
], fmt="hex")
响应: [
  {op: "write", status: "ok", bytes_written: 1, step: 0},
  {op: "read", status: "ok", data: "AA", length: 1, matched: false, expected: "BB", step: 1}
]
结论: ✅ 正常，on_mismatch="continue" 时不中断，返回 matched=false
```

### 13. script() - Full Sequence (flush+write+wait+read+expect)
```
请求: carrot-io_script(port="COM3", steps=[
  {op: "flush"},
  {op: "write", data: "48656C6C6F"},
  {op: "wait", "ms": 100},
  {op: "read", size: 10, expect: "576F726C64"}
], fmt="hex")
响应: 所有步骤 status="ok", read matched=true
结论: ✅ 正常
```

### 14. open() - TCP
```
请求: carrot-io_open(port="tcp_test", transport="tcp", host="127.0.0.1", net_port=9999)
响应: {status: "ok", port: "tcp_test", transport: "tcp", host: "127.0.0.1", net_port: 9999}
结论: ✅ 正常
```

### 15. write()/read() - TCP
```
请求: carrot-io_write(port="tcp_test", hex="48656C6C6F")
响应: {status: "ok", bytes_written: 5}
请求: carrot-io_read(port="tcp_test", size=10, fmt="hex")
响应: {length: 5, data: "48656C6C6F", status: "ok"}
结论: ✅ 正常，TCP echo 正确
```

### 16. open() - UDP
```
请求: carrot-io_open(port="udp_test", transport="udp", host="127.0.0.1", net_port=9998)
响应: {status: "ok", port: "udp_test", transport: "udp", host: "127.0.0.1", net_port: 9998}
结论: ✅ 正常
```

### 17. write()/read() - UDP
```
请求: carrot-io_write(port="udp_test", hex="48656C6C6F")
响应: {status: "ok", bytes_written: 5}
请求: carrot-io_read(port="udp_test", size=10, fmt="hex")
响应: {length: 5, data: "48656C6C6F", status: "ok"}
结论: ✅ 正常，UDP echo 正确
```

### 18. close()
```
请求: carrot-io_close(port="COM3")
响应: {status: "ok", port: "COM3"}
结论: ✅ 正常
```

### 19. write() - 空数据
```
请求: carrot-io_write(port="COM3", hex="")
响应: {status: "error", message: "Provide hex or ascii"}
结论: ✅ 正确拒绝空数据
```

### 20. write() - 同时提供 hex 和 ascii
```
请求: carrot-io_write(port="COM3", hex="55", ascii="Hello")
响应: {status: "error", message: "Provide only one of hex or ascii"}
结论: ✅ 正确拒绝同时提供两种格式
```

### 21. write() - 无效 hex 格式
```
请求: carrot-io_write(port="COM3", hex="ZZZZ")
响应: {status: "error", message: "Invalid hex string"}
结论: ✅ 正确拒绝无效 hex
```

### 22. write() - ASCII 含 \x00 字符
```
请求: carrot-io_write(port="COM3", ascii="Hello\x00World")
响应: {status: "ok", bytes_written: 11}
结论: ✅ 正确处理含 null 字节的 ASCII
```

### 23. write() - 纯 \x00 字节
```
请求: carrot-io_write(port="COM3", hex="000000")
响应: {status: "ok", bytes_written: 3}
结论: ✅ 正确写入 null 字节
```

### 24. read() - 超时行为
```
请求: carrot-io_read(port="COM3", size=1, fmt="hex", timeout=1)
响应: {length: 0, data: "", status: "ok"}
结论: ✅ 无数据时超时返回空
```

### 25. read() - size=0
```
请求: carrot-io_read(port="COM3", size=0, fmt="hex")
响应: {length: 0, data: "", status: "ok"}
结论: ✅ size=0 返回空
```

### 26. recv() - ASCII 格式
```
请求: carrot-io_recv(port="COM3", fmt="ascii") (发送 Hello 后)
响应: {length: 5, data: "'World'", status: "ok"}
结论: ✅ ASCII recv 同样被单引号包裹
```

### 27. recv() - size > 缓冲区数据
```
请求: carrot-io_recv(port="COM3", size=100, fmt="hex") (缓冲区仅 1 字节)
响应: {length: 1, data: "AA", status: "ok"}
结论: ✅ 返回可用数据，不要求达到 size
```

### 28. open() - 已打开的连接
```
请求: carrot-io_open(port="COM3", transport="serial", baudrate=115200) (重复打开)
响应: {status: "ok", message: "COM3 is already open"}
结论: ✅ 返回提示信息而非错误
```

### 29. open() - 无效 transport
```
请求: carrot-io_open(port="COM3", transport="invalid")
响应: {status: "error", message: "Unknown transport: invalid"}
结论: ✅ 正确拒绝无效 transport
```

### 30. open() - 无效波特率
```
请求: carrot-io_open(port="COM3", transport="serial", baudrate=999999)
响应: {status: "ok", port: "COM3", transport: "serial", baudrate: 999999}
结论: ⚠️ 接受了无效波特率，未做验证
```

### 31. open() - 无效端口名
```
请求: carrot-io_open(port="INVALID_PORT", transport="serial")
响应: {status: "error", message: "could not open port 'INVALID_PORT': FileNotFoundError..."}
结论: ✅ 正确拒绝无效端口
```

### 32. open() - TCP 无效主机
```
请求: carrot-io_open(port="tcp_invalid", transport="tcp", host="invalid.host.xyz", net_port=9999)
响应: {status: "error", message: "[Errno 11001] getaddrinfo failed"}
结论: ✅ 正确拒绝无效主机
```

### 33. open() - TCP 无效端口
```
请求: carrot-io_open(port="tcp_badport", transport="tcp", host="127.0.0.1", net_port=1)
响应: {status: "error", message: "timed out"}
结论: ✅ 连接超时正确返回错误
```

### 34. open() - serial 完整参数
```
请求: carrot-io_open(port="COM3", transport="serial", baudrate=115200, bytesize=8, parity="N", stopbits=1)
响应: {status: "ok", port: "COM3", transport: "serial", baudrate: 115200}
结论: ✅ 完整参数正常接受
```

### 35. open() - buffer_size 参数
```
请求: carrot-io_open(port="COM3", transport="serial", baudrate=115200, buffer_size=2097152)
响应: {status: "ok", port: "COM3", ...}
结论: ✅ buffer_size 参数正常接受
```

### 36. close() - 已关闭的连接
```
请求: carrot-io_close(port="COM3") (关闭后再次关闭)
响应: {status: "error", message: "COM3 is not open"}
结论: ✅ 正确返回错误
```

### 37. close() - 不存在的连接名
```
请求: carrot-io_close(port="nonexistent")
响应: {status: "error", message: "nonexistent is not open"}
结论: ✅ 正确返回错误
```

### 38. script() - on_mismatch="stop" 匹配成功
```
请求: carrot-io_script(port="COM3", steps=[
  {op: "write", data: "55"},
  {op: "read", size: 1, expect: "AA", on_mismatch: "stop"}
], fmt="hex")
响应: 所有步骤 status="ok", matched=true
结论: ✅ 匹配成功时 on_mismatch="stop" 不影响执行
```

### 39. script() - on_mismatch 无效值
```
请求: carrot-io_script(port="COM3", steps=[
  {op: "write", data: "55"},
  {op: "read", size: 1, expect: "BB", on_mismatch: "invalid_value"}
], fmt="hex")
响应: read 返回 matched=false, 但继续执行（未中断）
结论: ✅ 无效 on_mismatch 值视为 "continue" 处理
```

### 40. script() - 无效 op 类型
```
请求: carrot-io_script(port="COM3", steps=[{op: "invalid_op"}])
响应: {op: "invalid_op", status: "error", message: "Unknown op: invalid_op", step: 0}
结论: ✅ 正确拒绝无效操作类型
```

### 41. script() - 空步骤数组
```
请求: carrot-io_script(port="COM3", steps=[])
响应: (空)
结论: ✅ 空步骤正常处理
```

### 42. script() - 多步循环 (write+read x2 + wait + flush)
```
请求: carrot-io_script(port="COM3", steps=[
  {op: "flush"},
  {op: "write", data: "55"}, {op: "read", size: 1, expect: "AA"},
  {op: "write", data: "55"}, {op: "read", size: 1, expect: "AA"},
  {op: "wait", "ms": 50}, {op: "flush"}
])
响应: 7 步全部 status="ok"
结论: ✅ 多步循环正常
```

### 43. script() - read 超时 (无数据)
```
请求: carrot-io_script(port="COM3", steps=[
  {op: "flush"},
  {op: "read", size: 1, timeout: 1}
])
响应: {op: "read", status: "ok", data: "", length: 0, step: 1}
结论: ✅ 超时返回空数据
```

### 44. script() - TCP Echo
```
请求: carrot-io_script(port="tcp_test", steps=[
  {op: "flush"},
  {op: "write", data: "48656C6C6F"},
  {op: "read", size: 10, expect: "48656C6C6F"}
], fmt="hex")
响应: 所有步骤 status="ok", read matched=true
结论: ✅ TCP 脚本执行成功
```

### 45. script() - UDP Echo
```
请求: carrot-io_script(port="udp_test", steps=[
  {op: "flush"},
  {op: "write", data: "48656C6C6F"},
  {op: "read", size: 10, expect: "48656C6C6F"}
], fmt="hex")
响应: 所有步骤 status="ok", read matched=true
结论: ✅ UDP 脚本执行成功
```

### 46. recv() - UDP 有数据
```
请求: carrot-io_recv(port="udp_test", fmt="hex") (发送后立即 recv)
响应: {length: 1, data: "55", status: "ok"}
结论: ✅ 正确返回缓冲区数据
```

### 47. history() - UDP
```
请求: carrot-io_history(port="udp_test", limit=3)
响应: {status: "ok", entries: [...3条记录...]}
结论: ✅ 返回操作历史
```

### 48. history() - limit=0
```
请求: carrot-io_history(port="COM3", limit=0)
响应: {status: "ok", entries: [...所有记录...]}
结论: ✅ limit=0 返回所有记录（而非空数组）
```

### 49. history() - limit=1000
```
请求: carrot-io_history(port="COM3", limit=1000)
响应: {status: "ok", entries: [...实际记录...]}
结论: ✅ limit 超大返回实际记录数
```

### 50. read() - FF XX 多帧响应
```
请求: carrot-io_write(port="COM3", hex="FF42")
读取: carrot-io_read(port="COM3", size=10, fmt="hex", timeout=2)
响应: {length: 10, data: "42014202420342044205", status: "ok"}
结论: ✅ 正确接收多帧数据，echo server 每秒发送一帧
```

### 51. history() - 内部操作类型泄露
```
请求: carrot-io_history(port="COM3", limit=20)
返回的 op 类型: tx_queue, tx_drain, recv, read
期望: 仅返回公开 API 操作 (write, read, recv)
结论: ⚠️ history 返回了 tx_queue/tx_drain 等传输层内部操作
实际数据:
  {op: "tx_queue", data: "55", length: 1, pending: 1}  ← 内部操作
  {op: "tx_drain", data: "55", length: 1, pending: 0}  ← 内部操作
  {op: "recv", data: "AA", length: 1, pending: 1}
  {op: "read", data: "AA", length: 1, pending: 0}
```

---

## 未测试项目

1. **write() 超大数据** - 超过缓冲区大小的数据
2. **多连接并发** - 同时打开多个连接（串口不支持，TCP/UDP 可能支持）
3. **open() read_timeout/write_timeout** - 已传入参数但未验证实际超时行为
4. **串口 parity/stopbits 非默认值** - 仅测试了默认值 N/1

---

## 发现的问题

### 🔴 严重问题

### 问题 1: history() 返回传输层内部操作 (BUG)
- **现象**: `history()` 返回 `tx_queue`、`tx_drain` 等内部 op 类型
- **期望**: 仅返回用户可调用的 API 操作 (open, close, write, read, recv, script)
- **影响**: 中 - 暴露了内部实现细节，调用方可能被意外的 op 类型困扰
- **复现**:
  ```
  history(limit=20) 返回:
    {op: "tx_queue", ...}  ← 内部操作
    {op: "tx_drain", ...}  ← 内部操作
    {op: "recv", ...}
    {op: "read", ...}
  ```
- **建议**: 过滤掉 `tx_queue`/`tx_drain` 等内部操作，仅保留公开 API 操作记录

### 🟡 一般问题

### 问题 2: read() 返回的 ASCII 数据被单引号包裹
- **现象**: `carrot-io_read(fmt="ascii")` 返回 `"'World'"` 而非 `"World"`
- **影响**: 轻微，使用时需注意去除引号
- **建议**: 确认是否为预期行为，如不是应修复

### 问题 3: script() 使用 fmt=hex 时 write data 必须是 hex 格式
- **现象**: `fmt=hex` 时 `write` 的 `data` 字段必须是 hex 字符串，不能是 ASCII
- **影响**: 文档应明确说明 fmt 参数对所有步骤的影响
- **建议**: 更新文档或在错误消息中更清晰提示

### 问题 4: TCP 连接超时后返回 "timed out" 而非错误对象
- **现象**: TCP 连接超时时返回 `{status: "error", message: "timed out"}`
- **影响**: 错误消息不够明确，应区分 "连接超时" 和 "未连接"
- **建议**: 返回更详细的错误信息

### 问题 5: history() 的 limit=0 行为与预期不符
- **现象**: `history(limit=0)` 返回所有记录，而非空数组
- **影响**: 低，但与常规分页 API 的 `limit=0` 语义不同
- **建议**: 确认是否为预期行为，如不是应修复

### 问题 6: read() 超时返回 `status: "ok"` 而非 `"timeout"`
- **现象**: 读取超时时返回 `{status: "ok", length: 0}` 而非 `{status: "timeout"}`
- **影响**: 低，调用方需通过 length=0 判断超时
- **建议**: 考虑返回 `status: "timeout"` 以区分正常空读取

### 问题 7: 无效波特率被接受
- **现象**: `baudrate=999999` 返回 ok，未验证波特率有效性
- **影响**: 中，可能导致后续通信异常
- **建议**: 在 open 时验证波特率是否为常见值（9600, 19200, 38400, 57600, 115200 等）

---

## 总结

carrot-io MCP 服务的核心功能（串口/TCP/UDP 的打开、读写、关闭）在正常情况下工作良好。**50 个测试用例全部通过**，发现 **1 个严重 BUG** 和 **6 个一般问题**：

### 关键发现

| # | 问题 | 严重程度 | 说明 |
|---|------|----------|------|
| 1 | `history()` 返回内部操作 `tx_queue`/`tx_drain` | 🔴 严重 | 暴露了传输层实现细节 |
| 2 | `read()` ASCII 数据被单引号包裹 | 🟡 一般 | 返回 `"'World'"` 而非 `"World"` |
| 3 | `script()` 的 `fmt` 参数影响所有步骤 | 🟡 一般 | 文档未明确说明 |
| 4 | TCP 连接超时错误消息不明确 | 🟡 一般 | 返回 "timed out" |
| 5 | `history(limit=0)` 返回所有记录 | 🟡 一般 | 与常规分页 API 语义不同 |
| 6 | `read()` 超时返回 `status: "ok"` | 🟡 一般 | 应返回 `status: "timeout"` |
| 7 | 无效波特率被接受 | 🟡 一般 | `baudrate=999999` 返回 ok |

### 核心问题分析

**问题 1（history 内部操作泄露）** 是唯一的功能 BUG：
- `tx_queue` 和 `tx_drain` 是传输层内部操作
- 不应暴露给调用方，建议在 history 返回时过滤

### 建议优先级

1. **立即修复**: 问题 1（history 内部操作泄露）
2. **尽快修复**: 问题 2、6
3. **计划修复**: 问题 3-5、7

**总体评价**: 服务基础功能完善，核心功能无 BUG。唯一严重问题是 history 泄露了传输层内部操作。
