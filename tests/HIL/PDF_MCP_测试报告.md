# carrot-pdf MCP 服务测试报告

**测试日期**: 2026-07-01
**MCP 服务**: carrot-mcp-pdf v0.1.3
**测试环境**: 通过 MCP tool 直接调用
**VLM 配置**: 未配置 (vlm_model=None, vlm_configured=false)
**测试文件**: DI.pdf (29页, 无TOC), MF1S50YYX_V1.pdf (36页, 有TOC), JEP128.pdf (7页, 无TOC)

---

## 测试结果总览

| 方法 | 参数 | 状态 | 备注 |
|------|------|------|------|
| `version` | - | ✅ PASS | 返回 `{status, name, version, vlm_model, vlm_configured}` |
| `get_toc` | DI.pdf (无TOC, 29页) | ✅ PASS | has_toc=false, total_pages=29 |
| `get_toc` | MF1S50YYX_V1.pdf (有TOC, 36页) | ✅ PASS | has_toc=true, 返回完整目录树 |
| `get_toc` | JEP128.pdf (无TOC, 7页) | ✅ PASS | has_toc=false, total_pages=7 |
| `get_toc` | nonexistent.pdf | ✅ PASS | 返回 error "File not found" |
| `get_pages` | DI.pdf, pages="1", multimodal=true | ❌ FAIL | `'str' object has no attribute 'get'` |
| `get_pages` | DI.pdf, pages="1", multimodal=false | ❌ FAIL | 同上 |
| `get_pages` | MF1S50YYX_V1.pdf, pages="1-2", multimodal=true | ❌ FAIL | 同上 |
| `get_pages` | MF1S50YYX_V1.pdf, pages="1-2", multimodal=false | ❌ FAIL | 同上 |
| `get_pages` | JEP128.pdf, pages="1", multimodal=true | ❌ FAIL | 同上 |
| `get_pages` | JEP128.pdf, pages="1", multimodal=false | ❌ FAIL | 同上 |
| `get_pages` | DI.pdf, pages="1", force_ocr=true | ✅ PASS | 返回 VLM 未配置占位文本 |
| `get_pages` | JEP128.pdf, pages="1", force_ocr=true | ✅ PASS | 返回 VLM 未配置占位文本 |
| `get_pages` | DI.pdf, pages="100" (越界) | ✅ PASS | 返回 error "Pages out of range" |
| `get_pages` | DI.pdf, pages="abc" (无效) | ✅ PASS | 返回 error "Invalid page range" |
| `get_pages` | nonexistent.pdf, pages="1" | ✅ PASS | 返回 error "File not found" |
| `create_task` | DI.pdf, multimodal=true | ⚠️ WARN | 返回 task_id, 但后台转换静默失败(0页缓存) |
| `create_task` | MF1S50YYX_V1.pdf, multimodal=true | ⚠️ WARN | 同上 |
| `create_task` | JEP128.pdf, multimodal=true | ⚠️ WARN | 同上 |
| `get_status` | 有效的 task_id (DI.pdf) | ✅ PASS | 返回 completed, 100%, 29/29页 |
| `get_status` | 有效的 task_id (MF1S50YYX_V1.pdf) | ✅ PASS | 返回 completed, 100%, 36/36页 |
| `get_status` | 无效的 task_id | ✅ PASS | 返回 error "Task not found" |

**总计: 21 个测试用例, 13 通过, 6 FAIL, 2 WARN**

---

## 详细测试记录

### 1. version()
```
请求: carrot-pdf_version()
响应: {status: "ok", name: "carrot-mcp-pdf", version: "0.1.3", vlm_model: null, vlm_configured: false}
结论: ✅ 正常返回服务名称、版本号和 VLM 配置状态
```

### 2-4. get_toc() - 正常 PDF
```
请求: carrot-pdf_get_toc(pdf_path="...DI.pdf")
响应: {status: "ok", has_toc: false, total_pages: 29, message: "No TOC found..."}
结论: ✅ 无 TOC 的 PDF 正确返回 has_toc=false

请求: carrot-pdf_get_toc(pdf_path="...MF1S50YYX_V1.pdf")
响应: {status: "ok", has_toc: true, total_pages: 36, toc: [{level:1, title:"1  General description", start_page:1, end_page:1}, ...共60项]}
结论: ✅ 有 TOC 的 PDF 正确返回目录树，支持多级目录 (level 1-4)

请求: carrot-pdf_get_toc(pdf_path="...JEP128.pdf")
响应: {status: "ok", has_toc: false, total_pages: 7, message: "No TOC found..."}
结论: ✅ 无 TOC 的 PDF 正确返回
```

### 5. get_toc() - 文件不存在
```
请求: carrot-pdf_get_toc(pdf_path="...nonexistent.pdf")
响应: {status: "error", message: "File not found: ...nonexistent.pdf"}
结论: ✅ 正确返回文件不存在错误
```

### 6-11. get_pages() - pymupdf4llm 转换路径 (全部失败)
```
请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="1", multimodal=true)
响应: Error executing tool get_pages: 'str' object has no attribute 'get'
结论: ❌ pymupdf4llm.to_markdown() 返回 str, 但代码假设返回 dict/list

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="1", multimodal=false)
响应: Error executing tool get_pages: 'str' object has no attribute 'get'
结论: ❌ 同上, multimodal 参数不影响转换路径

请求: carrot-pdf_get_pages(pdf_path="...MF1S50YYX_V1.pdf", pages="1-2", multimodal=true)
响应: Error executing tool get_pages: 'str' object has no attribute 'get'
结论: ❌ 同上

请求: carrot-pdf_get_pages(pdf_path="...MF1S50YYX_V1.pdf", pages="1-2", multimodal=false)
响应: Error executing tool get_pages: 'str' object has no attribute 'get'
结论: ❌ 同上

请求: carrot-pdf_get_pages(pdf_path="...JEP128.pdf", pages="1", multimodal=true)
响应: Error executing tool get_pages: 'str' object has no attribute 'get'
结论: ❌ 同上

请求: carrot-pdf_get_pages(pdf_path="...JEP128.pdf", pages="1", multimodal=false)
响应: Error executing tool get_pages: 'str' object has no attribute 'get'
结论: ❌ 同上
```

### 12-13. get_pages() - force_ocr 路径
```
请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="1", force_ocr=true, multimodal=false)
响应: {status: "ok", pages: {"1": {content: [{type: "text", data: "[VLM model not configured, cannot force OCR]"}]}}, total_pages: 29}
结论: ✅ force_ocr 路径正常, VLM 未配置时返回占位文本

请求: carrot-pdf_get_pages(pdf_path="...JEP128.pdf", pages="1", force_ocr=true, multimodal=true)
响应: {status: "ok", pages: {"1": {content: [{type: "text", data: "[VLM model not configured, cannot force OCR]"}]}}, total_pages: 7}
结论: ✅ 同上
```

### 14-15. get_pages() - 错误处理
```
请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="100")
响应: {status: "error", message: "Pages out of range (total 29): [100]"}
结论: ✅ 越界页码正确返回错误

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="abc")
响应: {status: "error", message: "Invalid page range: invalid literal for int() with base 10: 'abc'"}
结论: ✅ 无效页码格式正确返回错误
```

### 16. get_pages() - 文件不存在
```
请求: carrot-pdf_get_pages(pdf_path="...nonexistent.pdf", pages="1")
响应: {status: "error", message: "File not found: ...nonexistent.pdf"}
结论: ✅ 正确返回文件不存在错误
```

### 17-19. create_task()
```
请求: carrot-pdf_create_task(pdf_path="...DI.pdf", multimodal=true)
响应: {status: "ok", task_id: "17b96a70_1782873128", total_pages: 29, message: "Background conversion started"}
结论: ⚠️ 返回 task_id 和页数, 但后台线程因同一 BUG 静默失败, 最终缓存 0 页

请求: carrot-pdf_create_task(pdf_path="...MF1S50YYX_V1.pdf", multimodal=true)
响应: {status: "ok", task_id: "3c695143_1782873185", total_pages: 36, message: "Background conversion started"}
结论: ⚠️ 同上

请求: carrot-pdf_create_task(pdf_path="...JEP128.pdf", multimodal=true)
响应: {status: "ok", task_id: "95ef0105_1782873238", total_pages: 7, message: "Background conversion started"}
结论: ⚠️ 同上
```

### 20-21. get_status()
```
请求: carrot-pdf_get_status(task_id="17b96a70_1782873128")
响应: {status: "ok", task_id: "17b96a70_1782873128", conversion_status: "completed", progress_percent: 100, current_page: 29, total_pages: 29, start_time: "2026-07-01T10:32:08"}
结论: ✅ 正确返回任务状态, 但状态不反映实际缓存失败

请求: carrot-pdf_get_status(task_id="nonexistent_task_id")
响应: {status: "error", message: "Task not found: nonexistent_task_id"}
结论: ✅ 正确返回任务不存在错误
```

---

## 发现的问题

### 🔴 严重问题

### 问题 1: get_pages() pymupdf4llm 转换路径崩溃 (BUG)
- **现象**: 所有 `get_pages` 调用 (force_ocr=false) 返回 `'str' object has no attribute 'get'`
- **根因**: `pymupdf4llm.to_markdown()` 返回 `str` (markdown 文本), 但 `server.py:178-188` 假设返回 `dict` 或 `list[dict]`
- **代码位置**: `server.py:178-188`
  ```python
  if isinstance(page_chunks, dict):
      page_chunks = [page_chunks]
  for i, chunk in enumerate(page_chunks):
      text = chunk.get("text", "")  # ← str 没有 .get() 方法
  ```
- **影响**: 🔴 **严重** — `get_pages` 核心功能完全不可用, 无法从任何 PDF 提取内容
- **修复方案**: 检查 `page_chunks` 是否为 `str`, 若是则直接作为整个文档的文本处理:
  ```python
  if isinstance(page_chunks, str):
      page_chunks = [{"text": page_chunks}]
  elif isinstance(page_chunks, dict):
      page_chunks = [page_chunks]
  ```

### 问题 2: create_task() 后台转换静默失败 (BUG)
- **现象**: `create_task` 返回 `status: "completed"` 且 `progress_percent: 100`, 但缓存中 **0 页被缓存**
- **根因**: `_convert_all` (`server.py:250-266`) 存在与 `get_pages` 相同的 str-vs-dict BUG, 且异常被 `except Exception: pass` 静默吞掉
- **代码位置**: `server.py:250-266` + `server.py:270`
  ```python
  chunk = pymupdf4llm.to_markdown(...)
  if isinstance(chunk, list):
      chunk = chunk[0] if chunk else {}
  text = chunk.get("text", "")  # ← str 没有 .get(), 异常被 pass
  ```
- **影响**: 🔴 **严重** — 后台全量转换功能完全无效, `create_task` 返回虚假成功状态
- **修复方案**: 同问题 1, 增加 `isinstance(chunk, str)` 检查

### 🟡 一般问题

### 问题 3: get_status() 不反映实际缓存状态
- **现象**: `get_status` 显示 `conversion_status: "completed"`, 但实际缓存中无页面数据
- **影响**: 🟡 中 — 用户误以为转换成功, 调用 `get_pages` 时才发现数据为空
- **建议**: `get_status` 应检查缓存中实际缓存的页数, 或在转换完成后验证缓存完整性

### 问题 4: create_task() 异常被静默吞掉
- **现象**: `_convert_all` 中 `except Exception: pass` (`server.py:270`) 导致所有转换错误不可见
- **影响**: 🟡 中 — 无法诊断转换失败原因, 任务状态不反映实际错误
- **建议**: 记录异常日志, 或在任务状态中记录失败页数和错误信息

### 问题 5: get_pages() force_ocr 路径返回格式不一致
- **现象**: `force_ocr=true` 时返回 `{pages: {"1": {content: [...]}}}`, 而文档描述的 `ocr_content` 字段未返回
- **代码位置**: `server.py:152-157`
  ```python
  cached_pages[str(page_num)] = {
      "content": content,
      "ocr_content": content,  # 存储了 ocr_content
  }
  ```
  但返回时 (`server.py:196-201`):
  ```python
  if use_ocr and "ocr_content" in page_data:
      result_pages[str(p)] = {"content": page_data["ocr_content"]}
  ```
- **影响**: 🟢 低 — 返回格式与缓存存储一致, 但 force_ocr 时 content 和 ocr_content 相同, 返回哪个无实质区别
- **建议**: 保持返回 `{content, ocr_content}` 双字段, 与文档描述一致

---

## 总结

carrot-pdf MCP 服务的 **5 个方法** 中, `version`、`get_toc`、`get_status` 工作正常, 但 **`get_pages` 核心转换功能完全不可用**, `create_task` 返回虚假成功状态。

### 关键发现

| # | 问题 | 严重程度 | 说明 |
|---|------|----------|------|
| 1 | `get_pages()` pymupdf4llm 路径崩溃 | 🔴 严重 | str-vs-dict 类型假设错误, 所有调用失败 |
| 2 | `create_task()` 静默失败, 缓存 0 页 | 🔴 严重 | 同一根因, 异常被 pass 吞掉 |
| 3 | `get_status()` 不反映实际缓存状态 | 🟡 一般 | 返回 completed 但无实际数据 |
| 4 | `_convert_all` 异常被静默吞掉 | 🟡 一般 | 无法诊断转换失败原因 |
| 5 | `force_ocr` 返回格式与文档不一致 | 🟢 低 | 返回单字段而非双字段 |

### 根因分析

**问题 1 和 2 的根因相同**: `pymupdf4llm.to_markdown()` 在当前版本返回 `str` (markdown 文本), 而非代码假设的 `dict` 或 `list[dict]`。这导致:

1. `get_pages()` 中: `page_chunks` 是 str → `for chunk in page_chunks` 遍历字符 → `chunk.get("text", "")` 崩溃
2. `_convert_all()` 中: `chunk` 是 str → `chunk.get("text", "")` 崩溃 → 被 `except Exception: pass` 吞掉

**修复优先级**:
1. **立即修复**: 问题 1 + 2 — 在 `server.py:178` 和 `server.py:259` 增加 `isinstance(str)` 检查
2. **尽快修复**: 问题 3 + 4 — 增加转换结果验证和异常日志
3. **低优先级**: 问题 5 — 统一返回格式

### 未测试项目

1. **force_ocr=true + VLM 已配置** — VLM 未配置, 无法测试实际 OCR 路径
2. **multimodal=true + 有图片的 PDF** — 因 BUG 无法进入图片处理路径
3. **并发 create_task** — 未测试多个后台任务同时运行
4. **缓存命中** — 因 BUG 无法创建缓存, 无法测试缓存读取路径
5. **CARROT_MCP_FORCE_MULTIMODAL 环境变量** — 未测试环境变量覆盖逻辑
