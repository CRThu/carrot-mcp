# carrot-pdf MCP 服务测试报告

**测试日期**: 2026-07-02
**MCP 服务**: carrot-mcp-pdf v0.2.0
**测试环境**: 通过 MCP tool 直接调用 (Software-in-the-Loop)
**VLM 配置**: 未配置 (vlm_model=None, vlm_configured=false)
**测试文件**:
- `DI.pdf` — 29页, 无TOC, 含图片页面 (中国国标文档)
- `MF1S50YYX_V1.pdf` — 36页, 有TOC (NXP MIFARE Classic 数据手册)
- `JEP128.pdf` — 7页, 无TOC (JEDEC 标准文档, 含图片)
- `FM552_EE map.xlsx` — 非PDF文件 (用于异常测试)

---

## 测试结果总览

| # | 方法 | 参数组合 | 状态 | 备注 |
|---|------|----------|------|------|
| 1 | `version` | — | ✅ PASS | 返回服务名、版本号、VLM 配置状态 |
| 2 | `get_toc` | DI.pdf (无TOC, 29页) | ✅ PASS | has_toc=false, total_pages=29 |
| 3 | `get_toc` | MF1S50YYX_V1.pdf (有TOC, 36页) | ✅ PASS | has_toc=true, 返回63项目录树 (level 1-4) |
| 4 | `get_toc` | JEP128.pdf (无TOC, 7页) | ✅ PASS | has_toc=false, total_pages=7 |
| 5 | `get_toc` | nonexistent.pdf | ✅ PASS | 返回 error "File not found" |
| 6 | `get_toc` | FM552_EE map.xlsx (非PDF) | ❌ FAIL | 返回 has_toc=false, total_pages=7 (错误地解析了xlsx文件) |
| 7 | `get_pages` | DI.pdf pages="1", multimodal=true | ✅ PASS | 纯文本页面, 返回 markdown 内容 + 图片附件 |
| 8 | `get_pages` | DI.pdf pages="5", multimodal=true | ✅ PASS | 含图片页面, 返回 ImageContent 附件 |
| 9 | `get_pages` | DI.pdf pages="1-3", multimodal=true | ✅ PASS | 多页文本, 返回完整内容 |
| 10 | `get_pages` | DI.pdf pages="1-3", multimodal=false | ✅ PASS | VLM未配置时回退返回图片附件 |
| 11 | `get_pages` | DI.pdf pages="29", multimodal=true | ✅ PASS | 最后一页, 纯文本 |
| 12 | `get_pages` | DI.pdf pages="1,5,10", multimodal=true | ✅ PASS | 非连续多页请求正常 |
| 13 | `get_pages` | DI.pdf pages="1", force_ocr=true | ✅ PASS | VLM未配置时回退返回图片附件 |
| 14 | `get_pages` | DI.pdf pages="1", force_ocr=true, multimodal=false | ✅ PASS | VLM未配置时回退返回图片附件 |
| 15 | `get_pages` | MF1S50YYX_V1.pdf pages="1-2", multimodal=true | ✅ PASS | page 1 含图片, 返回 ImageContent 附件 |
| 16 | `get_pages` | MF1S50YYX_V1.pdf pages="1-2", multimodal=false | ✅ PASS | VLM未配置时回退返回图片附件 |
| 17 | `get_pages` | MF1S50YYX_V1.pdf pages="1", force_ocr=true | ✅ PASS | 返回 "VLM model not configured, cannot force OCR" |
| 18 | `get_pages` | JEP128.pdf pages="1", multimodal=true | ✅ PASS | page 1 含图片, 返回 ImageContent 附件 |
| 19 | `get_pages` | JEP128.pdf pages="1", multimodal=false | ✅ PASS | VLM未配置时回退返回图片附件 |
| 20 | `get_pages` | JEP128.pdf pages="1-7", multimodal=true | ✅ PASS | 全部7页, 含图片页返回 ImageContent |
| 21 | `get_pages` | DI.pdf pages="100" (越界) | ✅ PASS | 返回 error "Pages out of range (total 29): [100]" |
| 22 | `get_pages` | DI.pdf pages="abc" (无效) | ✅ PASS | 返回 error "Invalid page range: invalid literal for int()" |
| 23 | `get_pages` | nonexistent.pdf pages="1" | ✅ PASS | 返回 error "File not found" |
| 24 | `get_pages` | FM552_EE map.xlsx pages="1", multimodal=true | ❌ FAIL | 非PDF文件被错误解析并返回表格内容 |
| 25 | `get_pages` | FM552_EE map.xlsx pages="1", multimodal=false | ❌ FAIL | 同上, 返回表格内容 |

**总计: 25 个测试用例, 22 PASS, 3 FAIL**

---

## 详细测试记录

### 1. version()
```
请求: carrot-pdf_version()
响应: {status: "ok", name: "carrot-mcp-pdf", version: "0.2.0", vlm_model: null, vlm_configured: false}
结论: ✅ 正常返回服务名称、版本号和 VLM 配置状态
```

### 2-6. get_toc()
```
请求: carrot-pdf_get_toc(pdf_path="...DI.pdf")
响应: {status: "ok", has_toc: false, total_pages: 29, message: "No TOC found..."}
结论: ✅ 无 TOC 的 PDF 正确返回 has_toc=false

请求: carrot-pdf_get_toc(pdf_path="...MF1S50YYX_V1.pdf")
响应: {status: "ok", has_toc: true, total_pages: 36, toc: [{level:1, title:"1 General description", start_page:1, end_page:1}, ...共63项]}
结论: ✅ 有 TOC 的 PDF 正确返回目录树, 支持多级目录 (level 1-4)

请求: carrot-pdf_get_toc(pdf_path="...JEP128.pdf")
响应: {status: "ok", has_toc: false, total_pages: 7, message: "No TOC found..."}
结论: ✅ 无 TOC 的 PDF 正确返回

请求: carrot-pdf_get_toc(pdf_path="...nonexistent.pdf")
响应: {status: "error", message: "File not found: ...nonexistent.pdf"}
结论: ✅ 正确返回文件不存在错误

请求: carrot-pdf_get_toc(pdf_path="...FM552_EE map.xlsx")
响应: {status: "ok", has_toc: false, total_pages: 7, message: "No TOC found..."}
结论: ❌ 非PDF文件被错误地解析, 返回了 total_pages=7 (应返回 "Unsupported file type" 错误)
```

### 7-23. get_pages() — 各种参数组合
```
请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="1", multimodal=true)
响应: {status: "ok", total_pages: 29, pages: ["1"]} + markdown 内容 + ImageContent 附件
结论: ✅ 纯文本页面正确返回 markdown + 图片附件

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="5", multimodal=true)
响应: {status: "ok", total_pages: 29, pages: ["5"]} + markdown 内容 + ImageContent 附件
结论: ✅ 含图片页面正确返回 ImageContent 附件

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="1-3", multimodal=true)
响应: {status: "ok", total_pages: 29, pages: ["1", "2", "3"]} + 完整 markdown 内容
结论: ✅ 多页请求正常

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="1-3", multimodal=false)
响应: {status: "ok", total_pages: 29, pages: ["1", "2", "3"]} + "[VLM model not configured, returning image as attachment]" + 图片附件
结论: ✅ multimodal=false + VLM未配置时回退返回图片附件 (设计行为)

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="29", multimodal=true)
响应: {status: "ok", total_pages: 29, pages: ["29"]} + markdown 内容
结论: ✅ 最后一页正常返回

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="1,5,10", multimodal=true)
响应: {status: "ok", total_pages: 29, pages: ["1", "5", "10"]} + 完整内容
结论: ✅ 非连续多页请求正常

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="1", force_ocr=true)
响应: {status: "ok", total_pages: 29, pages: ["1"]} + "[VLM model not configured, returning image as attachment]" + 图片附件
结论: ✅ force_ocr=true + VLM未配置时回退返回图片附件

请求: carrot-pdf_get_pages(pdf_path="...MF1S50YYX_V1.pdf", pages="1", force_ocr=true)
响应: {status: "ok", total_pages: 36, pages: ["1"]} + "[VLM model not configured, cannot force OCR]"
结论: ✅ force_ocr=true + VLM未配置时返回特殊提示

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="100")
响应: {status: "error", message: "Pages out of range (total 29): [100]"}
结论: ✅ 越界页码正确返回错误

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="abc")
响应: {status: "error", message: "Invalid page range: invalid literal for int() with base 10: 'abc'"}
结论: ✅ 无效页码格式正确返回错误

请求: carrot-pdf_get_pages(pdf_path="...nonexistent.pdf", pages="1")
响应: {status: "error", message: "File not found: ...nonexistent.pdf"}
结论: ✅ 正确返回文件不存在错误
```

### 24-25. get_pages() — 非PDF文件异常测试
```
请求: carrot-pdf_get_pages(pdf_path="...FM552_EE map.xlsx", pages="1", multimodal=true)
响应: {status: "ok", total_pages: 7, pages: ["1"]} + 表格内容 (NFC T2T memory map)
结论: ❌ 非PDF文件被错误解析并返回了无意义的表格内容

请求: carrot-pdf_get_pages(pdf_path="...FM552_EE map.xlsx", pages="1", multimodal=false)
响应: 同上
结论: ❌ 非PDF文件被错误解析
```

---

## 发现的问题

### 问题 1: ❌ get_toc() 不校验文件类型, 非PDF文件被错误解析

- **现象**: `get_toc` 对 `.xlsx` 文件未做类型检查, 被 pymupdf4llm 错误解析并返回 `has_toc: false, total_pages: 7`
- **代码位置**: `server.py` — get_toc 函数入口
- **影响**: 🟡 中 — 非PDF文件被当作PDF处理, 返回无意义的结果
- **建议**: 在 `get_toc` 入口处检查文件扩展名, 非 `.pdf` 返回 `{status: "error", message: "Unsupported file type: .xlsx"}`

### 问题 2: ❌ get_pages() 不校验文件类型, 非PDF文件被错误处理

- **现象**: 与 get_toc 相同, 非PDF文件会被尝试解析并返回无意义的表格内容
- **影响**: 🟡 中 — 可能导致不可预期的错误或返回错误数据
- **建议**: 在 `get_pages` 入口处增加文件类型检查

### 问题 3: ⚠️ force_ocr=true 在不同PDF上行为不一致

- **现象**: 
  - DI.pdf + force_ocr=true: 返回 "VLM model not configured, returning image as attachment"
  - MF1S50YYX_V1.pdf + force_ocr=true: 返回 "VLM model not configured, cannot force OCR"
- **影响**: 🟢 低 — 两种情况都是VLM未配置时的回退行为, 但提示信息不一致
- **建议**: 统一 force_ocr 在 VLM 未配置时的提示信息

---

## 已知限制

### 限制 1: 中文/公式 PDF 文本提取乱码 (非代码 BUG)

- **现象**: DI.pdf 等中文国标文档, `pymupdf4llm.to_markdown()` 输出的数学符号和部分中文字符被错误映射为生僻汉字 (如 `犖＝` 应为 `N＝`, `犘＿狏犪犾狌犐` 应为 `P_value`)
- **验证**: 使用 Adobe Acrobat 复制相同内容, 输出同样乱码
- **根因**: PDF 文件本身的字体编码 (ToUnicode CMap) 缺失或损坏。这是文档生成工具的问题, 任何文本提取库都无法修复
- **推荐方案**: 使用 `force_ocr=true` + 配置 VLM, 通过渲染页面为图片后 OCR 识别

---

## 未测试项目

| 项目 | 原因 |
|------|------|
| `force_ocr=true` + VLM 已配置 | VLM 未配置, 无法测试实际 OCR 路径 |
| `CARROT_MCP_FORCE_MULTIMODAL` 环境变量覆盖 | 未设置该环境变量 |
| 超大 PDF (>100页) | test_input 中无此类文件 |
| 加密/损坏的 PDF | 未测试异常 PDF 处理 |
| 并发 get_pages 调用 | 未测试多任务同时运行 |

---

## 总结

carrot-pdf MCP 服务 v0.2.0 的 **3 个方法** 测试结果:

- ✅ **`version`** — 完全正常
- ⚠️ **`get_toc`** — PDF文件正常, **非PDF文件未校验** (返回错误结果)
- ⚠️ **`get_pages`** — PDF文件正常返回, **非PDF文件未校验**, force_ocr 行为在不同PDF上不一致

**测试通过率**: 22/25 (88%)

**存在的问题**:
- ❌ get_toc/get_pages 不校验文件类型, 非PDF文件被错误处理
- ⚠️ force_ocr=true 在不同PDF上的回退提示信息不一致

**已知限制**: 中文/公式 PDF 的文本提取乱码是 PDF 文件本身编码问题, 非代码 BUG。唯一解决方案是通过 `force_ocr=true` + VLM 进行图片 OCR 识别。
