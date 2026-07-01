# carrot-mcp-nfc 硬件在环测试报告

- **测试时间**: 2026-06-30
- **MCP 服务**: carrot-mcp-nfc v0.1.1
- **测试卡片**: NTAG213 (UID: 5AD5E377014189)

---

## 方法测试结果总览

| 方法 | PN532 | CLRC663 | 说明 |
|------|:-----:|:-------:|------|
| `version` | ✅ | ✅ | |
| `list_readers` | ✅ | ✅ | |
| `connect` | ✅ | ✅ | |
| `disconnect` | ✅ | ✅ | |
| `field_on` | ✅ | ✅ | |
| `field_off` | ✅ | ✅ | |
| `find` | ✅ | ✅ | |
| `transceive` | ✅ | ✅ | 基本功能正常 |
| `exchange` | ✅ | ✅ | |
| `trace_get` | ✅ | ✅ | |
| `trace_clear` | ✅ | ✅ | |
| `script` | ✅ | ✅ | 基本功能正常 |
| `reqa` | ❌ | ❌ | 未实现 |
| `wupa` | ❌ | ❌ | 未实现 |
| `halt` | ❌ | ❌ | 未实现 |
| `select` | ❌ | ❌ | 参数不匹配 |
| `anticoll` | ❌ | ❌ | 未实现 |

---

## 1. carrot-nfc_version

| 项目 | 结果 |
|------|------|
| 状态 | ✅ PASS |
| 返回值 | `{status: "ok", name: "carrot-mcp-nfc", version: "0.1.1"}` |
| 说明 | 无参数，正常返回服务名称和版本号 |

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

---

## 4. carrot-nfc_disconnect

| 项目 | 结果 |
|------|------|
| 状态 | ✅ PASS |
| 返回值 | `{status: "ok"}` |

---

## 5. carrot-nfc_field_on

| 项目 | 结果 |
|------|------|
| 状态 | ✅ PASS |

---

## 6. carrot-nfc_field_off

| 项目 | 结果 |
|------|------|
| 状态 | ✅ PASS |

---

## 7. carrot-nfc_find

| 项目 | 结果 |
|------|------|
| 状态 | ✅ PASS |
| 返回值 | `uid="5AD5E377014189"`, `sak="0x0"` |

> PN532 ATQ=`0044`，CLRC663 ATQ=`4400`（字节序不同，属正常差异）

---

## 8. carrot-nfc_transceive

### 8.1 基本 READ 命令

| 测试用例 | 参数 | PN532 | CLRC663 |
|----------|------|:-----:|:-------:|
| READ page 0-3 | `data="3000"` | ✅ `5AD5E3E477014189BE480000E1101200` | ✅ 同 |
| READ page 4-7 | `data="3004"` | ✅ `DEADBEEF340300FE0000000000000000` | ✅ 同 |
| tx_crc=True, rx_crc=True | 默认 | ✅ | ✅ |

### 8.2 tx_crc / rx_crc 参数

| 参数组合 | PN532 | CLRC663 |
|----------|-------|---------|
| `tx_crc=False` | ❌ 返回空字符串 | ❌ `"No response from card"` |
| `rx_crc=False` | ❌ 返回空字符串 | ❌ `"No response from card"` |

> **差异**: PN532 静默失败（空字符串），CLRC663 返回明确错误信息

### 8.3 last_tx_bits 参数

| 参数 | PN532 | CLRC663 |
|------|-------|---------|
| `last_tx_bits=7, data="60"` | ⚠️ 返回空 | ❌ `"No response from card"` |

> 已激活状态下发送 REQA 不会再响应，属预期行为

### 8.4 无效输入

| 测试用例 | 结果 |
|----------|------|
| `data="ZZZZ"` | ✅ 两读卡器均返回 `"Invalid hex string"` |

---

## 9. carrot-nfc_exchange

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| READ page 0-3 | ✅ `5AD5E3E477014189BE480000E1101200` | ✅ 同 |
| READ page 4-7 | ✅ `DEADBEEF340300FE0000000000000000` | ✅ 同 |

> exchange 使用 InDataExchange（自动加 CRC），transceive 使用 InCommunicateThru（可配置 CRC）。正常场景下两者结果一致。

---

## 10. carrot-nfc_reqa

| 项目 | 结果 |
|------|------|
| 状态 | ❌ **未实现** |
| PN532 错误 | `'PN532_HSU' object has no attribute 'reqa'` |
| CLRC663 错误 | `'CLRC663' object has no attribute 'reqa'` |

---

## 11. carrot-nfc_wupa

| 项目 | 结果 |
|------|------|
| 状态 | ❌ **未实现** |
| PN532 错误 | `'PN532_HSU' object has no attribute 'wupa'` |
| CLRC663 错误 | `'CLRC663' object has no attribute 'wupa'` |

---

## 12. carrot-nfc_halt

| 项目 | 结果 |
|------|------|
| 状态 | ❌ **未实现** |
| PN532 错误 | `'PN532_HSU' object has no attribute 'halt'` |
| CLRC663 错误 | `'CLRC663' object has no attribute 'halt'` |

---

## 13. carrot-nfc_select

| 项目 | 结果 |
|------|------|
| 状态 | ❌ **参数不匹配** |
| PN532 错误 | `PN532_HSU.select() got an unexpected keyword argument 'cl_level'` |
| CLRC663 错误 | `CLRC663.select() got an unexpected keyword argument 'cl_level'` |

> MCP 层定义了 `cl_level` 和 `uid` 参数，但底层驱动方法签名不接受这些参数。

---

## 14. carrot-nfc_anticoll

| 项目 | 结果 |
|------|------|
| 状态 | ❌ **未实现** |
| PN532 错误 | `'PN532_HSU' object has no attribute 'anticoll'` |
| CLRC663 错误 | `'CLRC663' object has no attribute 'anticoll'` |

---

## 15. carrot-nfc_script

### 15.1 正常流程

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| find → exchange × 2 | ✅ | ✅ |
| exchange × 2（无 find） | ✅ | ✅ |
| field_off → wait → field_on → find → transceive × 2 | ✅ | ✅ |
| find → transceive × 6（全页读取 page 0-23） | ✅ | ✅ |

### 15.2 错误处理

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| find → transceive → transceive(invalid hex) | ✅ 中止并报错 | ✅ 中止并报错 |

### 15.3 未实现 op

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| find → exchange → halt | ❌ halt 失败 | ❌ halt 失败 |

---

## 16. carrot-nfc_trace_get

| 测试用例 | PN532 | CLRC663 |
|----------|:-----:|:-------:|
| 全部日志 | ✅ | ✅ |
| `level="DEBUG"` 过滤 | ✅ | ✅ |
| `layer="DRIVER"` 过滤 | ✅ | ✅ |
| `layer="PROTOCOL"` 过滤 | ✅ (空) | ✅ (有内容) |

> **差异**: CLRC663 的 PROTOCOL 层有 TX/RX 原始数据和命令解析日志；PN532 只有 DRIVER 层。

---

## 17. carrot-nfc_trace_clear

| 项目 | 结果 |
|------|------|
| 状态 | ✅ PASS |
| 确认 | clear 后 trace_get 返回 `[]` |

---

## 问题汇总

### 5 个未实现/不兼容的方法

| 方法 | 问题 | 严重性 |
|------|------|--------|
| `reqa` | 底层驱动未实现 | 🔴 功能缺失 |
| `wupa` | 底层驱动未实现 | 🔴 功能缺失 |
| `halt` | 底层驱动未实现 | 🔴 功能缺失 |
| `anticoll` | 底层驱动未实现 | 🔴 功能缺失 |
| `select` | MCP 层参数与底层签名不匹配 | 🔴 接口不兼容 |

### 2 个读卡器行为差异

| 差异点 | PN532 | CLRC663 |
|--------|-------|---------|
| transceive 失败时 | 返回空字符串（静默失败） | 返回 `"No response from card"`（明确错误） |
| trace PROTOCOL 层 | 无内容 | 有 TX/RX 原始数据 |

### 建议

1. **实现 reqa/wupa/halt/anticoll/select**: 补充底层驱动的 ISO14443-3A 基础方法
2. **修复 select 参数签名**: MCP 层参数需与底层驱动对齐
3. **统一错误处理**: PN532 的 transceive 失败应返回明确错误而非空字符串
4. **script 中校验 op 可用性**: 执行未实现 op 前应提前报错
