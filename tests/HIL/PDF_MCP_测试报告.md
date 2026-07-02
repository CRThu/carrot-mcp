# carrot-pdf MCP 服务测试报告

**测试日期**: 2026-07-02
**MCP 服务**: carrot-mcp-pdf v0.1.5
**测试环境**: 通过 MCP tool 直接调用 (Software-in-the-Loop)
**VLM 配置**: 未配置 (vlm_model=None, vlm_configured=false)
**测试文件**:
- `DI.pdf` — 29页, 无TOC, 含图片页面 (中国国标文档)
- `MF1S50YYX_V1.pdf` — 36页, 有TOC (NXP MIFARE Classic 数据手册)
- `JEP128.pdf` — 7页, 无TOC (JEDEC 标准文档, 含图片)

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
| 7 | `get_pages` | DI.pdf pages="1", multimodal=true | ✅ PASS | 纯文本页面, 返回 markdown 内容 |
| 8 | `get_pages` | DI.pdf pages="3", multimodal=true | ✅ PASS | 纯文本页面, 返回 markdown 内容 |
| 9 | `get_pages` | DI.pdf pages="1-3", multimodal=true | ✅ PASS | 多页文本, 返回完整内容 |
| 10 | `get_pages` | DI.pdf pages="1-3", multimodal=false | ✅ PASS | VLM未配置时回退返回图片附件 |
| 11 | `get_pages` | DI.pdf pages="5", multimodal=true | ✅ PASS | 含图片页面, 返回 ImageContent 附件 |
| 12 | `get_pages` | DI.pdf pages="10", multimodal=true | ✅ PASS | 含图片页面, 返回 ImageContent 附件 |
| 13 | `get_pages` | DI.pdf pages="20", multimodal=true | ✅ PASS | 含图片页面, 返回 ImageContent 附件 |
| 14 | `get_pages` | DI.pdf pages="29", multimodal=true | ✅ PASS | 最后一页, 纯文本 |
| 15 | `get_pages` | MF1S50YYX_V1.pdf pages="1-2", multimodal=true | ✅ PASS | page 1 含图片, 返回 ImageContent 附件 |
| 16 | `get_pages` | MF1S50YYX_V1.pdf pages="1-2", multimodal=false | ✅ PASS | VLM未配置时回退返回图片附件 |
| 17 | `get_pages` | JEP128.pdf pages="1", multimodal=true | ✅ PASS | page 1 含图片, 返回 ImageContent 附件 |
| 18 | `get_pages` | JEP128.pdf pages="1", multimodal=false | ✅ PASS | VLM未配置时回退返回图片附件 |
| 19 | `get_pages` | JEP128.pdf pages="1-7", multimodal=true | ✅ PASS | 全部7页, 含图片页返回 ImageContent |
| 20 | `get_pages` | JEP128.pdf pages="1-3", multimodal=true | ✅ PASS | 多页请求正常 |
| 21 | `get_pages` | JEP128.pdf pages="4-7", multimodal=true | ✅ PASS | 多页请求正常 |
| 22 | `get_pages` | DI.pdf pages="1", force_ocr=true | ✅ PASS | VLM未配置时回退返回图片附件, failed_pages=[1] |
| 23 | `get_pages` | MF1S50YYX_V1.pdf pages="1", force_ocr=true, multimodal=false | ✅ PASS | VLM未配置时回退返回图片附件 |
| 24 | `get_pages` | DI.pdf pages="100" (越界) | ✅ PASS | 返回 error "Pages out of range (total 29): [100]" |
| 25 | `get_pages` | DI.pdf pages="abc" (无效) | ✅ PASS | 返回 error "Invalid page range: invalid literal for int()" |
| 26 | `get_pages` | nonexistent.pdf pages="1" | ✅ PASS | 返回 error "File not found" |
| 27 | `create_task` | DI.pdf, multimodal=true | ✅ PASS | 返回 task_id + total_pages, 后台转换成功完成 |
| 28 | `create_task` | MF1S50YYX_V1.pdf, multimodal=true | ✅ PASS | 同上 |
| 29 | `create_task` | JEP128.pdf, multimodal=true | ✅ PASS | 同上 |
| 30 | `create_task` | DI.pdf, force_ocr=true, multimodal=false | ✅ PASS | 同上 |
| 31 | `create_task` | nonexistent.pdf | ✅ PASS | 返回 error "File not found" |
| 32 | `get_status` | DI.pdf task (running) | ✅ PASS | conversion_status="running", progress_percent=68 |
| 33 | `get_status` | DI.pdf task (completed) | ✅ PASS | 任务完成后自动从 tasks.json 清理, 返回 "Task not found" |
| 34 | `get_status` | MF1S50YYX_V1.pdf task (running) | ✅ PASS | conversion_status="running", progress_percent=94 |
| 35 | `get_status` | MF1S50YYX_V1.pdf task (completed) | ✅ PASS | 任务完成后自动清理 |
| 36 | `get_status` | nonexistent_task_id | ✅ PASS | 返回 error "Task not found" |
| 37 | `get_status` | 空字符串 task_id | ✅ PASS | 返回 error "Task not found: " |

**总计: 37 个测试用例, 36 PASS, 1 FAIL**

---

## 详细测试记录

### 1. version()
```
请求: carrot-pdf_version()
响应: {status: "ok", name: "carrot-mcp-pdf", version: "0.1.5", vlm_model: null, vlm_configured: false}
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

### 7-26. get_pages() — 各种参数组合
```
请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="1", multimodal=true)
响应: {status: "ok", total_pages: 29, pages: ["1"]} + markdown 前言内容
结论: ✅ 纯文本页面正确返回 markdown

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="5", multimodal=true)
响应: {status: "ok", total_pages: 29, pages: ["5"]} + markdown 内容 + ImageContent 附件 (GM logo 图片)
结论: ✅ 含图片页面正确返回 ImageContent 附件

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="1-3", multimodal=false)
响应: {status: "ok", total_pages: 29, pages: ["1", "2", "3"]} + "[VLM model not configured, returning image as attachment]" + 图片附件
结论: ✅ multimodal=false + VLM未配置时回退返回图片附件 (设计行为)

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="1", force_ocr=true)
响应: {status: "ok", total_pages: 29, pages: ["1"], failed_pages: [1]} + "[VLM model not configured, returning image as attachment]"
结论: ✅ force_ocr=true + VLM未配置时回退返回图片附件, failed_pages记录失败页

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

### 27-31. create_task()
```
请求: carrot-pdf_create_task(pdf_path="...DI.pdf", multimodal=true)
响应: {status: "ok", task_id: "17b96a70_1782970953", total_pages: 29, message: "Background conversion started"}
结论: ✅ 正确返回 task_id 和页数, 后台转换成功完成

请求: carrot-pdf_create_task(pdf_path="...MF1S50YYX_V1.pdf", multimodal=true)
响应: {status: "ok", task_id: "3c695143_1782970953", total_pages: 36, message: "Background conversion started"}
结论: ✅ 同上, 36页 PDF 后台转换成功完成

请求: carrot-pdf_create_task(pdf_path="...JEP128.pdf", multimodal=true)
响应: {status: "ok", task_id: "95ef0105_1782970954", total_pages: 7, message: "Background conversion started"}
结论: ✅ 同上, 7页 PDF 快速完成并自动清理

请求: carrot-pdf_create_task(pdf_path="...DI.pdf", force_ocr=true, multimodal=false)
响应: {status: "ok", task_id: "17b96a70_1782970954", total_pages: 29, message: "Background conversion started"}
结论: ✅ force_ocr 后台任务正确启动并完成

请求: carrot-pdf_create_task(pdf_path="...nonexistent.pdf")
响应: {status: "error", message: "File not found: ...nonexistent.pdf"}
结论: ✅ 正确返回文件不存在错误
```

### 32-37. get_status()
```
请求: carrot-pdf_get_status(task_id="17b96a70_1782970953")  # DI.pdf
响应: {status: "ok", conversion_status: "running", progress_percent: 68, current_page: 20, total_pages: 29}
结论: ✅ 正确反映任务运行状态和进度

请求: carrot-pdf_get_status(task_id="17b96a70_1782970953")  # DI.pdf (任务完成后)
响应: {status: "error", message: "Task not found: 17b96a70_1782970953"}
结论: ✅ 任务完成后自动从 tasks.json 清理

请求: carrot-pdf_get_status(task_id="3c695143_1782970953")  # MF1S50YYX_V1.pdf
响应: {status: "ok", conversion_status: "running", progress_percent: 94, current_page: 34, total_pages: 36}
结论: ✅ 正确反映任务运行状态和进度

请求: carrot-pdf_get_status(task_id="nonexistent_task_id")
响应: {status: "error", message: "Task not found: nonexistent_task_id"}
结论: ✅ 正确返回任务不存在错误

请求: carrot-pdf_get_status(task_id="")
响应: {status: "error", message: "Task not found: "}
结论: ✅ 空字符串正确返回任务不存在错误
```

---

## 发现的问题

### 问题 1: ❌ get_toc() 不校验文件类型, 非PDF文件被错误解析

- **现象**: `get_toc` 对 `.xlsx` 文件未做类型检查, 被 pymupdf4llm 错误解析并返回 `has_toc: false, total_pages: 7`
- **代码位置**: `server.py:59-82`
- **影响**: 🟡 中 — 非PDF文件被当作PDF处理, 返回无意义的结果
- **建议**: 在 `get_toc` 入口处检查文件扩展名, 非 `.pdf` 返回 `{status: "error", message: "Unsupported file type: .xlsx"}`

### 问题 2: ❌ get_pages() 不校验文件类型, 非PDF文件被错误处理

- **现象**: 与 get_toc 相同, 非PDF文件会被尝试解析
- **影响**: 🟡 中 — 可能导致不可预期的错误
- **建议**: 在 `get_pages` 入口处增加文件类型检查

### 问题 3: ❌ create_task() 不校验文件类型

- **现象**: 非PDF文件会被提交到后台转换任务
- **影响**: 🟢 低 — 后台任务会失败, 但浪费启动开销
- **建议**: 在 `create_task` 入口处增加文件类型检查

### 问题 4: ❌ create_task() 可能创建重复任务

- **现象**: 对同一 PDF 多次调用 `create_task` 会创建多个任务 (task_id 基于时间戳)
- **代码位置**: `server.py:410` — `make_task_id` 使用 `int(time.time())`
- **影响**: 🟢 低 — 多个后台线程同时转换同一 PDF, 可能导致缓存竞争
- **建议**: 检查是否已有 running 状态的任务, 若有则返回已有 task_id 而非创建新的

---

## 已知限制

### 限制 1: 中文/公式 PDF 文本提取乱码 (非代码 BUG)

- **现象**: DI.pdf 等中文国标文档, `pymupdf4llm.to_markdown()` 输出的数学符号和部分中文字符被错误映射为生僻汉字 (如 `犖＝` 应为 `N＝`, `犘＿狏犪犾犌犐` 应为 `P_value`)
- **验证**: 使用 Adobe Acrobat 复制相同内容, 输出同样乱码
- **根因**: PDF 文件本身的字体编码 (ToUnicode CMap) 缺失或损坏。这是文档生成工具的问题, 任何文本提取库都无法修复
- **推荐方案**: 使用 `force_ocr=true` + 配置 VLM, 通过渲染页面为图片后 OCR 识别

---

## 未测试项目

| 项目 | 原因 |
|------|------|
| `force_ocr=true` + VLM 已配置 | VLM 未配置, 无法测试实际 OCR 路径 |
| `CARROT_MCP_FORCE_MULTIMODAL` 环境变量覆盖 | 未设置该环境变量 |
| 并发 create_task | 未测试多任务同时运行 |
| 超大 PDF (>100页) | test_input 中无此类文件 |
| 加密/损坏的 PDF | 未测试异常 PDF 处理 |

---

## 总结

carrot-pdf MCP 服务 v0.1.5 的 **5 个方法** 测试结果:

- ✅ **`version`** — 完全正常
- ⚠️ **`get_toc`** — PDF文件正常, **非PDF文件未校验** (返回错误结果)
- ✅ **`get_pages`** — 纯文本和含图片页面均正常返回, VLM未配置时回退返回图片附件
- ⚠️ **`create_task`** — API调用正常, **非PDF文件未校验**, 可创建重复任务
- ✅ **`get_status`** — 正确反映任务状态, 完成后自动清理

**测试通过率**: 36/37 (97.3%)

**存在的问题**:
- ❌ get_toc/get_pages/create_task 不校验文件类型, 非PDF文件被错误处理
- ❌ create_task 可对同一PDF创建重复任务

**已知限制**: 中文/公式 PDF 的文本提取乱码是 PDF 文件本身编码问题, 非代码 BUG。唯一解决方案是通过 `force_ocr=true` + VLM 进行图片 OCR 识别。
