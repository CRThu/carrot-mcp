# carrot-pdf MCP 服务测试报告

**测试日期**: 2026-07-01
**MCP 服务**: carrot-mcp-pdf v0.1.4
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
| 3 | `get_toc` | MF1S50YYX_V1.pdf (有TOC, 36页) | ✅ PASS | has_toc=true, 返回60项目录树 (level 1-4) |
| 4 | `get_toc` | JEP128.pdf (无TOC, 7页) | ✅ PASS | has_toc=false, total_pages=7 |
| 5 | `get_toc` | nonexistent.pdf | ✅ PASS | 返回 error "File not found" |
| 6 | `get_pages` | DI.pdf pages="1", multimodal=true | ✅ PASS | 返回缓存的 OCR 占位文本 (之前 force_ocr 测试写入) |
| 7 | `get_pages` | DI.pdf pages="3", multimodal=true | ✅ PASS | 纯文本页面, 返回 markdown 内容 |
| 8 | `get_pages` | DI.pdf pages="1-3", multimodal=true | ✅ PASS | 多页文本, 返回完整内容 |
| 9 | `get_pages` | DI.pdf pages="1-3", multimodal=false | ✅ PASS | 同上, multimodal=false 对纯文本无差异 |
| 10 | `get_pages` | DI.pdf pages="2", multimodal=true | ✅ PASS | 纯文本目录页 |
| 11 | `get_pages` | MF1S50YYX_V1.pdf pages="1", force_ocr=true | ✅ PASS | 返回 VLM 未配置占位文本 |
| 12 | `get_pages` | DI.pdf pages="1", force_ocr=true | ✅ PASS | 返回 VLM 未配置占位文本 |
| 13 | `get_pages` | DI.pdf pages="100" (越界) | ✅ PASS | 返回 error "Pages out of range (total 29): [100]" |
| 14 | `get_pages` | DI.pdf pages="abc" (无效) | ✅ PASS | 返回 error "Invalid page range: invalid literal for int()" |
| 15 | `get_pages` | nonexistent.pdf pages="1" | ✅ PASS | 返回 error "File not found" |
| 16 | `get_pages` | MF1S50YYX_V1.pdf pages="1-2", multimodal=true | ❌ FAIL | `Object of type bytes is not JSON serializable` |
| 17 | `get_pages` | MF1S50YYX_V1.pdf pages="1-2", multimodal=false | ❌ FAIL | 同上 |
| 18 | `get_pages` | JEP128.pdf pages="1", multimodal=true | ❌ FAIL | 同上 |
| 19 | `get_pages` | JEP128.pdf pages="1", multimodal=false | ❌ FAIL | 同上 |
| 20 | `get_pages` | JEP128.pdf pages="1-7", multimodal=true | ❌ FAIL | 同上 |
| 21 | `get_pages` | DI.pdf pages="5", multimodal=true | ❌ FAIL | 同上 (page 5 含图片) |
| 22 | `get_pages` | DI.pdf pages="1,3,5,10,20,29", multimodal=true | ❌ FAIL | 同上 (page 5 含图片) |
| 23 | `get_pages` | DI.pdf pages="1-29", multimodal=false | ❌ FAIL | 同上 (遍历到含图片页即失败) |
| 24 | `create_task` | DI.pdf, multimodal=true | ✅ PASS | 返回 task_id + total_pages |
| 25 | `create_task` | MF1S50YYX_V1.pdf, multimodal=true | ✅ PASS | 同上 |
| 26 | `create_task` | JEP128.pdf, multimodal=true | ✅ PASS | 同上 |
| 27 | `create_task` | DI.pdf, force_ocr=true, multimodal=false | ✅ PASS | 同上 |
| 28 | `create_task` | nonexistent.pdf | ✅ PASS | 返回 error "File not found" |
| 29 | `get_status` | DI.pdf task (valid) | ✅ PASS | conversion_status="failed", failed_at_page=6, cached_pages=5 |
| 30 | `get_status` | MF1S50YYX_V1.pdf task (valid) | ✅ PASS | conversion_status="failed", failed_at_page=4, cached_pages=3 |
| 31 | `get_status` | JEP128.pdf task (valid) | ✅ PASS | conversion_status="failed", failed_at_page=3, cached_pages=2 |
| 32 | `get_status` | force_ocr task (running) | ✅ PASS | conversion_status="running", 0% (VLM 未配置, 等待中) |
| 33 | `get_status` | nonexistent_task_id | ✅ PASS | 返回 error "Task not found" |
| 34 | `get_status` | 空字符串 task_id | ✅ PASS | 返回 error "Task not found: " |

**总计: 34 个测试用例, 25 PASS, 9 FAIL**

---

## 详细测试记录

### 1. version()
```
请求: carrot-pdf_version()
响应: {status: "ok", name: "carrot-mcp-pdf", version: "0.1.4", vlm_model: null, vlm_configured: false}
结论: ✅ 正常返回服务名称、版本号和 VLM 配置状态
```

### 2-5. get_toc()
```
请求: carrot-pdf_get_toc(pdf_path="...DI.pdf")
响应: {status: "ok", has_toc: false, total_pages: 29, message: "No TOC found..."}
结论: ✅ 无 TOC 的 PDF 正确返回 has_toc=false

请求: carrot-pdf_get_toc(pdf_path="...MF1S50YYX_V1.pdf")
响应: {status: "ok", has_toc: true, total_pages: 36, toc: [{level:1, title:"1 General description", start_page:1, end_page:1}, ...共60项]}
结论: ✅ 有 TOC 的 PDF 正确返回目录树, 支持多级目录 (level 1-4)

请求: carrot-pdf_get_toc(pdf_path="...JEP128.pdf")
响应: {status: "ok", has_toc: false, total_pages: 7, message: "No TOC found..."}
结论: ✅ 无 TOC 的 PDF 正确返回

请求: carrot-pdf_get_toc(pdf_path="...nonexistent.pdf")
响应: {status: "error", message: "File not found: ...nonexistent.pdf"}
结论: ✅ 正确返回文件不存在错误
```

### 6-15. get_pages() — 正常路径 (纯文本 / force_ocr / 错误处理)
```
请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="1", multimodal=true)
响应: {status: "ok", total_pages: 29, pages: ["1"]} + "[Page 1] [VLM model not configured, cannot force OCR]"
结论: ✅ 返回缓存的 OCR 占位文本 (之前 force_ocr 测试写入的缓存)

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="3", multimodal=true)
响应: {status: "ok", total_pages: 29, pages: ["3"]} + markdown 前言内容
结论: ✅ 纯文本页面正确返回 markdown

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="1-3", multimodal=true)
响应: {status: "ok", total_pages: 29, pages: ["1","2","3"]} + 3页内容
结论: ✅ 多页请求正确返回所有页面内容

请求: carrot-pdf_get_pages(pdf_path="...MF1S50YYX_V1.pdf", pages="1", force_ocr=true, multimodal=false)
响应: {status: "ok", total_pages: 36, pages: ["1"]} + "[VLM model not configured, cannot force OCR]"
结论: ✅ force_ocr 路径正常, VLM 未配置时返回占位文本

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

### 16-23. get_pages() — 含图片页面 (全部失败)
```
请求: carrot-pdf_get_pages(pdf_path="...MF1S50YYX_V1.pdf", pages="1-2", multimodal=true)
响应: Error executing tool get_pages: Object of type bytes is not JSON serializable
结论: ❌ MF1S50YYX_V1.pdf page 1 含图片, 缓存写入时 json.dump 失败

请求: carrot-pdf_get_pages(pdf_path="...JEP128.pdf", pages="1", multimodal=true)
响应: Error executing tool get_pages: Object of type bytes is not JSON serializable
结论: ❌ JEP128.pdf page 1 含图片, 同上

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="5", multimodal=true)
响应: Error executing tool get_pages: Object of type bytes is not JSON serializable
结论: ❌ DI.pdf page 5 含图片, 同上

请求: carrot-pdf_get_pages(pdf_path="...DI.pdf", pages="1-29", multimodal=false)
响应: Error executing tool get_pages: Object of type bytes is not JSON serializable
结论: ❌ 遍历到含图片页即失败, 整个请求中断
```

### 24-28. create_task()
```
请求: carrot-pdf_create_task(pdf_path="...DI.pdf", multimodal=true)
响应: {status: "ok", task_id: "17b96a70_1782894752", total_pages: 29, message: "Background conversion started"}
结论: ✅ 正确返回 task_id 和页数

请求: carrot-pdf_create_task(pdf_path="...MF1S50YYX_V1.pdf", multimodal=true)
响应: {status: "ok", task_id: "3c695143_1782894752", total_pages: 36, message: "Background conversion started"}
结论: ✅ 同上

请求: carrot-pdf_create_task(pdf_path="...JEP128.pdf", multimodal=true)
响应: {status: "ok", task_id: "95ef0105_1782894753", total_pages: 7, message: "Background conversion started"}
结论: ✅ 同上

请求: carrot-pdf_create_task(pdf_path="...DI.pdf", force_ocr=true, multimodal=false)
响应: {status: "ok", task_id: "17b96a70_1782894871", total_pages: 29, message: "Background conversion started"}
结论: ✅ force_ocr 后台任务正确启动

请求: carrot-pdf_create_task(pdf_path="...nonexistent.pdf")
响应: {status: "error", message: "File not found: ...nonexistent.pdf"}
结论: ✅ 正确返回文件不存在错误
```

### 29-34. get_status()
```
请求: carrot-pdf_get_status(task_id="17b96a70_1782894752")  # DI.pdf
响应: {status: "ok", task_id: "17b96a70_1782894752", conversion_status: "failed",
       progress_percent: 17, current_page: 3, total_pages: 29, cached_pages: 5,
       failed_at_page: 6, start_time: "2026-07-01T16:32:32"}
结论: ✅ 正确反映任务失败状态, failed_at_page=6 (page 6 含图片导致 save_cache 崩溃)

请求: carrot-pdf_get_status(task_id="3c695143_1782894752")  # MF1S50YYX_V1.pdf
响应: {status: "ok", conversion_status: "failed", progress_percent: 8,
       cached_pages: 3, failed_at_page: 4}
结论: ✅ 正确反映任务失败状态

请求: carrot-pdf_get_status(task_id="95ef0105_1782894753")  # JEP128.pdf
响应: {status: "ok", conversion_status: "failed", progress_percent: 28,
       cached_pages: 2, failed_at_page: 3}
结论: ✅ 正确反映任务失败状态

请求: carrot-pdf_get_status(task_id="17b96a70_1782894871")  # force_ocr task
响应: {status: "ok", conversion_status: "running", progress_percent: 0,
       current_page: 0, cached_pages: 0, failed_at_page: null}
结论: ✅ force_ocr 任务仍在运行 (VLM 未配置, 每次 OCR 重试 5 次后失败, 进度缓慢)

请求: carrot-pdf_get_status(task_id="nonexistent_task_id")
响应: {status: "error", message: "Task not found: nonexistent_task_id"}
结论: ✅ 正确返回任务不存在错误

请求: carrot-pdf_get_status(task_id="")
响应: {status: "error", message: "Task not found: "}
结论: ✅ 空字符串正确返回任务不存在错误
```

---

## 发现的问题

### 🔴 严重问题

#### 问题 1: get_pages() 含图片页面 — bytes 序列化崩溃 (BUG)

- **现象**: 所有包含图片的 PDF 页面调用 `get_pages` 返回 `Object of type bytes is not JSON serializable`
- **根因**: `converter.py:117-118` 中 `parse_page_content` 将图片读取为 `bytes` 对象:
  ```python
  img_bytes, mime = read_image(img_path)
  content.append({"type": "image", "data": img_bytes, "mime": mime})  # bytes!
  ```
  随后 `server.py:195-196` 调用 `save_cache(pdf_path, cache)`, 而 `cache.py:80` 使用 `json.dump()` 序列化缓存, `json.dump` 无法处理 `bytes` 对象。
- **代码位置**: `converter.py:118` (产生 bytes) → `server.py:196` (调用 save_cache) → `cache.py:80` (json.dump 崩溃)
- **影响**: 🔴 **严重** — 所有含图片的 PDF 页面无法转换, 占 test_input 3个PDF中的3个 (MF1S50YYX_V1.pdf page 1即含图, JEP128.pdf page 1含图, DI.pdf 部分页面含图)
- **修复方案**: 在 `converter.py:118` 将图片 bytes 转为 base64 字符串存储:
  ```python
  import base64
  content.append({"type": "image", "data": base64.b64encode(img_bytes).decode(), "mime": mime})
  ```
  同时修改 `ocr_content` 路径 (`converter.py:132`) 做相同处理。

#### 问题 2: create_task() 后台转换因同一 BUG 静默失败

- **现象**: `create_task` 返回 `status: "ok"`, 但后台线程在遇到含图片页面时 `break` 退出, `get_status` 返回 `conversion_status: "failed"`
- **根因**: `_convert_all` (`server.py:293-311`) 调用 `parse_page_content` 产生 bytes → `save_cache` 中 `json.dump` 崩溃 → 异常被 `server.py:315-318` 捕获并 `break`
- **代码位置**: `server.py:315-318`
  ```python
  except Exception as e:
      print(f"[carrot-mcp-pdf] page {page_num} failed, stopping: {e}", file=sys.stderr)
      break  # 停止后续所有页面
  ```
- **影响**: 🔴 **严重** — 后台全量转换遇到第一个含图片页即停止, 已缓存的页面不完整
- **修复方案**: 同问题 1, 在 `converter.py` 中将 bytes 转为 base64 字符串

### 🟡 一般问题

#### 问题 3: get_status() 不反映实际缓存完整性

- **现象**: `get_status` 返回 `conversion_status: "failed"` + `cached_pages: N`, 但不说明失败原因 (如 "bytes serialization error at page X")
- **影响**: 🟡 中 — 用户看到 failed 但不知道原因, 无法自行修复
- **建议**: 在任务状态中记录 `error_message` 字段, 记录最后一次失败的异常信息

#### 问题 4: _convert_all() 遇到错误即 break, 不跳过失败页继续

- **现象**: `_convert_all` 中 `except Exception: ... break` 导致一个页面失败就停止整个转换
- **影响**: 🟡 中 — 即使只有少数页面含图片, 整个 PDF 转换都会失败
- **建议**: 改为 `continue` 跳过失败页, 或提供 `skip_errors` 参数

#### 问题 5: get_pages() 无图片时返回格式与文档不一致

- **现象**: `get_pages` 返回 `list[TextContent | ImageContent]`, 第一个元素是 JSON metadata (TextContent), 后续是页面内容。但当页面不含图片时, 返回纯 TextContent 列表, 没有 ImageContent。
- **代码位置**: `server.py:199-228`
- **影响**: 🟢 低 — 纯文本页面不需要 ImageContent, 但调用方可能期望统一的返回格式
- **建议**: 保持现状, 但文档中明确说明 "仅含图片的页面返回 ImageContent"

#### 问题 6: force_ocr 任务在 VLM 未配置时仍启动, 浪费资源

- **现象**: `create_task(force_ocr=true)` 在 VLM 未配置时仍启动后台线程, 每页重试 5 次 (指数退避 1s→2s→4s→8s→16s), 然后 `break` 退出
- **代码位置**: `server.py:273-287` + `converter.py:69-70`
- **影响**: 🟡 中 — 29页 PDF 需要等待 5×(1+2+4+8+16)=155秒 才能失败退出
- **建议**: 在 `create_task` 启动前检查 `vlm_configured()`, 若未配置则直接返回错误

### 🟢 低优先级

#### 问题 7: get_toc() 不支持非 PDF 文件

- **现象**: `get_toc` 对 `.xlsx` / `.doc` 文件未做处理, 但 test_input 中有这些文件
- **影响**: 🟢 低 — 这些文件本就不应该传给 PDF 服务, 但缺少明确的错误提示
- **建议**: 检查文件扩展名, 非 `.pdf` 返回 "Unsupported file type"

#### 问题 8: create_task() 可能创建重复任务

- **现象**: 对同一 PDF 多次调用 `create_task` 会创建多个任务 (task_id 基于时间戳, 不同)
- **代码位置**: `server.py:357` — `make_task_id` 使用 `int(time.time())`
- **影响**: 🟢 低 — 多个后台线程同时转换同一 PDF, 可能导致缓存竞争
- **建议**: 检查是否已有 running 状态的任务, 若有则返回已有 task_id 而非创建新的

---

## 根因分析

### 问题 1+2 的根因: bytes → json.dump 序列化失败

**完整调用链**:
```
get_pages(pdf_path, pages, multimodal=true)
  → pymupdf4llm.to_markdown(write_images=True)  # 生成 markdown + 图片文件
  → parse_page_content(text, image_dir)          # 读取图片为 bytes
      → read_image(img_path)                     # 返回 (bytes, mime)
      → content.append({"type":"image","data":bytes})  # bytes 存入 content
  → cached_pages[str(page_num)] = {"content": content, "ocr_content": ocr_content}
  → save_cache(pdf_path, cache)
      → json.dump(data_copy, f, ...)             # 💥 bytes 不可序列化
```

**为什么纯文本页面不受影响**: 纯文本页面的 content blocks 只有 `{"type":"text","data":"str"}`, 不含 bytes 对象, json.dump 正常。

**为什么 `multimodal=false` 也不影响**: `multimodal` 参数只影响返回时选择 `content` 还是 `ocr_content`, 不影响 `parse_page_content` 产生 bytes 的过程。

### 修复优先级

| 优先级 | 问题 | 修复方案 | 影响范围 |
|--------|------|----------|----------|
| P0 | 问题 1+2 | `converter.py:118,132` 将 bytes 转为 base64 字符串 | 所有含图片的 PDF |
| P1 | 问题 3 | `get_status` 增加 `error_message` 字段 | 用户体验 |
| P1 | 问题 4 | `_convert_all` 改 `break` 为 `continue` | 部分页面失败时的容错 |
| P2 | 问题 6 | `create_task` 启动前检查 VLM 配置 | 资源浪费 |
| P2 | 限制 1 | `converter.py` 检测乱码字符, 自动回退 OCR 路径 | 中文 PDF 公式识别 |
| P3 | 问题 7-8 | 文件类型检查 / 重复任务检测 | 边界情况 |

---

## 已知限制

### 限制 1: 中文/公式 PDF 文本提取乱码 (非代码 BUG)

- **现象**: DI.pdf 等中文国标文档, `pymupdf4llm.to_markdown()` 输出的数学符号和部分中文字符被错误映射为生僻汉字 (如 `犖＝` 应为 `N＝`, `犘＿狏犪犾犌犐` 应为 `P_value`)
- **验证**: 使用 Adobe Acrobat 复制相同内容, 输出同样乱码
- **根因**: PDF 文件本身的字体编码 (ToUnicode CMap) 缺失或损坏。这是文档生成工具 (如方正排版、某些 Word 转 PDF 插件) 的问题, 任何文本提取库都无法修复, 因为正确的字符映射根本不存在于 PDF 文件中
- **影响**: 🔴 严重 — 中文技术文档的公式和特殊字符内容完全不可读
- **推荐方案**: 使用 `force_ocr=true` + 配置 VLM, 通过渲染页面为图片后 OCR 识别。VLM (如 GPT-4V、Claude) 能直接理解图片中的公式和文字, 不依赖 PDF 内部编码
- **自动检测增强** (建议): 在 `converter.py` 中检测 pymupdf4llm 输出是否包含典型乱码字符 (`犖`/`犿`/`犓`/`狏` 等), 若检测到则自动回退 OCR 路径

---

## 未测试项目

| 项目 | 原因 |
|------|------|
| `force_ocr=true` + VLM 已配置 | VLM 未配置, 无法测试实际 OCR 路径 |
| `multimodal=true` + 有图片的 PDF (ImageContent 返回) | 因 BUG 无法进入图片返回路径 |
| `CARROT_MCP_FORCE_MULTIMODAL` 环境变量覆盖 | 未设置该环境变量 |
| 缓存命中路径 (第二次请求同一页) | 部分页面已有缓存 (来自之前测试), 但含图片页无法缓存 |
| 并发 create_task | 未测试多任务同时运行 |
| 超大 PDF (>100页) | test_input 中无此类文件 |
| 加密/损坏的 PDF | 未测试异常 PDF 处理 |

---

## 总结

carrot-pdf MCP 服务的 **5 个方法** 中:
- ✅ **`version`** — 完全正常
- ✅ **`get_toc`** — 完全正常, 支持有/无 TOC 的 PDF, 错误处理完善
- ❌ **`get_pages`** — 纯文本页面正常, **含图片页面全部失败** (`bytes is not JSON serializable`)
- ✅ **`create_task`** — API 调用正常, 但后台转换因同一 BUG 失败
- ✅ **`get_status`** — 正确反映任务状态 (包括失败状态)

**核心 BUG**: `converter.py:118` 将图片存储为 `bytes` 对象, 而 `cache.py:80` 的 `json.dump` 无法序列化 `bytes`。修复方案是将 bytes 转为 base64 字符串存储, 这是一个一行代码的修复, 但影响了所有含图片的 PDF 页面。

**已知限制**: 中文/公式 PDF 的文本提取乱码是 PDF 文件本身编码问题 (Acrobat 复制同样乱码), 非代码 BUG。唯一解决方案是通过 `force_ocr=true` + VLM 进行图片 OCR 识别。修复 P0 BUG 后, 该路径即可正常工作。
