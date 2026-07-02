# carrot-mcp-nfc 硬件在环测试报告

- **测试时间**: 2026-07-02
- **MCP 服务**: carrot-mcp-nfc v0.2.0
- **测试卡片**: NTAG213 (PN532: UID=5AD5E377014189, CLRC663: UID=5AF5337C014189)

---

## 方法测试结果总览

| 方法 | PN532 | CLRC663 | 说明 |
|------|:-----:|:-------:|------|
| `version` | ✅ | ✅ | |
| `list_readers` | ✅ | ✅ | |
| `connect` | ✅ | ✅ | ⚠️ transport 仅支持 serial |
| `disconnect` | ✅ | ✅ | |
| `field_on` | ✅ | ✅ | |
| `field_off` | ✅ | ✅ | |
| `find` | ✅ | ✅ | ⚠️ 高级模式 ATQA 字节序不同 |
| `transceive` | ⚠️ | ⚠️ | ⚠️ last_rx_bits 不一致; ⚠️ tx_crc=False 无响应 |
| `reqa` | ✅ | ✅ | |
| `wupa` | ✅ | ✅ | |
| `halt` | ✅ | ✅ | |
| `select` | ⚠️ | ⚠️ | CL2 SELECT 驱动 trace 标注误判 |
| `anticoll` | ⚠️ | ⚠️ | ⚠️ bits 不一致; ❌ uid_prefix 无响应 |
| `trace_get` | ✅ | ✅ | |
| `trace_clear` | ✅ | ✅ | |
| `script` | ⚠️ | ⚠️ | ⚠️ wait 仅 PN532 验证 |

---

## 1. carrot-nfc_version

| 项目 | 结果 |
|------|------|
| 状态 | ✅ PASS |
| 返回值 | `{status: "ok", name: "carrot-mcp-nfc", version: "0.2.0"}` |

---

## 2. carrot-nfc_list_readers

| 项目 | 结果 |
|------|------|
| 状态 | ✅ PASS |
| 返回值 | `readers: ["pn532", "clrc663"]`, `transports: ["serial"]` |

---

## 3. carrot-nfc_connect

| 项目 | 结果 |
|------|------|
| 状态 | ✅ PASS |
| 测试参数 | `port=COM20, reader_type=pn532` / `port=COM4, reader_type=clrc663` |
| 返回 | 均 `{status: "ok"}` |
| ⚠️ | `transport` 参数仅支持 `"serial"`，无法测试其他传输类型 |

---

## 4. carrot-nfc_disconnect

| 项目 | 结果 |
|------|------|
| 状态 | ✅ PASS |
| 返回值 | `{status: "ok"}` |

---

## 5. carrot-nfc_field_on / field_off

| 项目 | 结果 |
|------|------|
| 状态 | ✅ PASS |

---

## 6. carrot-nfc_find

### 6.1 高级模式 (low_level=False)

| 读卡器 | 结果 | UID | ATQ | SAK |
|--------|:----:|-----|-----|-----|
| PN532 | ✅ | `5AD5E377014189` | `0044` | `0x0` |
| CLRC663 | ✅ | `5AF5337C014189` | `4400` | `0x0` |

> ⚠️ ATQA 字节序不同: PN532=`0044`, CLRC663=`4400`。驱动层字节序差异。

### 6.2 低级模式 (low_level=True)

| 读卡器 | 结果 | UID | ATQ | SAK |
|--------|:----:|-----|-----|-----|
| PN532 | ✅ | `5AD5E377014189` | `4400` | `0x0` |
| CLRC663 | ✅ | `5AF5337C014189` | `4400` | `0x0` |

> ⚠️ PN532 高级模式 ATQ=`0044`，低级模式 ATQ=`4400`，同一读卡器两种模式 ATQA 字节序不一致。

---

## 7. carrot-nfc_transceive

### 7.1 基本 READ 命令

| 测试用例 | PN532 | CLRC663 |
|----------|-------|---------|
| READ page 0-3 (`data="3000"`) | ✅ `5AD5E3E477014189BE480000E1101200` | ✅ `5AF533147C014189B5480000E1101200` |
| READ page 4-7 (`data="3004"`) | ✅ `DEADBEEF340300FE0000000000000000` | ✅ `0103A00C340300FE0000000000000000` |

### 7.2 无效输入

| 测试用例 | 结果 |
|----------|------|
| `data="ZZZZ"` | ✅ 两读卡器均返回 `"Invalid hex string"` |

### 7.3 tx_crc / rx_crc

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| `tx_crc=False, rx_crc=True` | ⚠️ "No response" | ⚠️ "No response" |
| `tx_crc=True, rx_crc=False` | ⚠️ 返回 18 字节 (含 CRC 末尾 2 字节) | ⚠️ 返回 18 字节 (含 CRC 末尾 2 字节) |

> ⚠️ `tx_crc=False`: 发送帧不含 CRC，卡片拒绝，无响应。功能正确但无错误提示，调用者无法区分"卡片不存在"与"CRC 被拒绝"。
> ⚠️ `rx_crc=False`: 返回数据包含 CRC 字节 (length=18 而非 16)，调用者需自行剥离末尾 2 字节。

### 7.4 last_tx_bits (短帧)

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| REQA via transceive (`data="26", last_tx_bits=7, tx_crc=False, rx_crc=False`) | ✅ `data="4400"` | ✅ `data="4400"` |

### 7.5 last_rx_bits 不一致

| 读卡器 | last_rx_bits (READ 响应) |
|--------|------------------------|
| PN532 | `0` |
| CLRC663 | `8` |

> ❌ 两读卡器对同一字节对齐响应报告不同: PN532=`0`, CLRC663=`8`。上层依赖 `last_rx_bits` 判断响应完整性时行为不一致。

---

## 8. carrot-nfc_reqa

| 项目 | 结果 |
|------|------|
| 状态 | ✅ PASS |
| PN532 | `{status: "ok", data: "4400", length: 2}` |
| CLRC663 | `{status: "ok", data: "4400", length: 2}` |

---

## 9. carrot-nfc_wupa

| 项目 | 结果 |
|------|------|
| 状态 | ✅ PASS |
| PN532 | `{status: "ok", data: "4400", length: 2}` |
| CLRC663 | `{status: "ok", data: "4400", length: 2}` |

---

## 10. carrot-nfc_halt

| 项目 | 结果 |
|------|------|
| 状态 | ✅ PASS |

---

## 11. carrot-nfc_select

### 11.1 CL1 SELECT

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| `cl_level=1, uid="885AD5E3E4"` / `"885AF53314"` | ✅ `data="04"` (SAK=0x04) | ✅ `data="04"` (SAK=0x04) |

### 11.2 CL2 SELECT

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| 完整流程: reqa → anticoll CL1 → select CL1 → anticoll CL2 → select CL2 | ✅ `data="00"` (SAK=0x00) | ✅ `data="00"` (SAK=0x00) |
| CL2 SELECT 后 transceive READ | ✅ 返回正确页面数据 | ✅ 返回正确页面数据 |

> ⚠️ `data="00"` 是 SAK=0x00（ISO 14443-3A 最后级联层标准响应），**不是 NACK**。但驱动层 trace 将其标注为 `[NACK — Not authenticated / Parity error]`，为驱动层误判。

---

## 12. carrot-nfc_anticoll

### 12.1 基本 anticoll

| 读卡器 | 结果 | data | bits |
|--------|:----:|------|------|
| PN532 | ✅ | `885AD5E3E4` | `0` |
| CLRC663 | ✅ | `885AF53314` | `8` |

> ❌ 两读卡器 bits 报告不一致: PN532=`0`, CLRC663=`8`。均为字节对齐响应，但返回值不同。

### 12.2 anticoll uid_prefix

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| `cl_level=1, nvb=33, uid_prefix="5A"` | ❌ "No response" | ❌ "No response" |

> ❌ `uid_prefix` 参数在两读卡器上均返回 "No response"。可能原因: (1) 单卡环境无碰撞场景; (2) `nvb` + `uid_prefix` 组合帧构造异常; (3) 驱动层未正确处理 partial UID anticollision。

### 12.3 anticoll bits 差异

| 读卡器 | bits |
|--------|------|
| PN532 | `0` |
| CLRC663 | `8` |

> ❌ 同 12.1，两读卡器 bits 返回值不一致。

---

## 13. carrot-nfc_script

### 13.1 正常流程

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| find → transceive × 2 | ✅ | ✅ |
| field_off → wait → field_on → find → transceive × 2 | ✅ | ✅ |
| find → transceive × 16 (全页读取 page 0-15) | ✅ | ✅ |
| reqa → anticoll → select → halt → wupa | ✅ | ✅ |
| field_off → wait → field_on → find(low_level) → transceive × 2 | ✅ | ✅ |
| reqa → anticoll CL1 → select CL1 → anticoll CL2 → select CL2 → transceive | ✅ | ✅ |

### 13.2 expect 匹配

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| find(expect=UID) → transceive(expect=正确数据) | ✅ matched=true | ✅ matched=true |

### 13.3 expect_bits 位级匹配

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| reqa(expect="4400", expect_bits=4) | ✅ matched=true | ✅ matched=true |
| reqa(expect="4401", expect_bits=4, on_mismatch="continue") | ✅ matched=false | ✅ matched=false |

### 13.4 expect 不匹配 + on_mismatch

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| transceive(expect=错误值, on_mismatch="continue") → 继续执行 | ✅ matched=false, 后续步骤继续 | ✅ 同 |
| transceive(expect=错误值, on_mismatch="stop") → 中止 | ✅ matched=false, status="error" | ✅ 同 |

### 13.5 错误处理

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| transceive(invalid hex) | ✅ "Invalid hex string" | ✅ 同 |
| unknown op | ✅ "Unknown op: xxx" | ✅ 同 |

### 13.6 wait 时序

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| field_off → wait(1500ms) → field_on → reqa | ✅ | ⚠️ 未测试 |

> ⚠️ `wait` 仅在 PN532 上验证，CLRC663 未覆盖。

### 13.7 全页读取边界

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| READ page 0x3C (超出 NTAG213 范围) | ✅ "No response" | ✅ "No response" |

---

## 14. carrot-nfc_trace_get

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| 全部日志 | ✅ | ✅ |
| `level="DEBUG"` 过滤 | ✅ | ✅ |
| `layer="DRIVER"` 过滤 | ✅ | ✅ |
| `layer="PROTOCOL"` 过滤 | ✅ | ✅ |

---

## 15. carrot-nfc_trace_clear

| 项目 | 结果 |
|------|------|
| 状态 | ✅ PASS |

---

## 问题汇总

| # | 问题 | 严重性 | 位置 |
|---|------|:------:|------|
| 1 | `transceive` last_rx_bits 两读卡器不一致 (PN532=`0`, CLRC663=`8`) | ⚠️ | §7.5 |
| 2 | `anticoll` bits 两读卡器不一致 (PN532=`0`, CLRC663=`8`) | ⚠️ | §12.1 |
| 3 | `find` 高级模式 ATQA 字节序不同 (PN532=`0044`, CLRC663=`4400`) | ⚠️ | §6.1 |
| 4 | `find` PN532 高级/低级模式 ATQA 不一致 (`0044` vs `4400`) | ⚠️ | §6.1/6.2 |
| 5 | `transceive` tx_crc=False 无错误提示，与"卡片不存在"不可区分 | ⚠️ | §7.3 |
| 6 | `transceive` rx_crc=False 返回含 CRC 的额外 2 字节 | ⚠️ | §7.3 |
| 7 | `select` CL2 驱动 trace 误标 `[NACK]`，实际为 SAK=0x00 | ⚠️ | §11.2 |
| 8 | `anticoll` uid_prefix 两读卡器均返回 "No response" | ❌ | §12.2 |
| 9 | `script` wait 仅 PN532 验证，CLRC663 未覆盖 | ⚠️ | §13.6 |
| 10 | `connect` transport 仅支持 serial，无法测试其他传输类型 | ⚠️ | §3 |
