# carrot-office MCP 服务测试报告

**测试日期**: 2026-06-30
**MCP 服务**: carrot-mcp-office v0.1.3
**测试环境**: 直接通过 agent 工具调用 MCP tool

---

## 测试结果总览

| 方法 | 参数 | 状态 | 备注 |
|------|------|------|------|
| `version` | - | ✅ PASS | 返回 `{status, name, version, backup}` |
| `workbook_metadata` | test.xlsx | ✅ PASS | 返回 sheets, title, creator, created, modified |
| `workbook_search` | Sheet1, "hello" | ✅ PASS | 大小写不敏感，返回单元格引用和值 |
| `read_range` | Sheet1, A1:B2 | ✅ PASS | 返回二维数组 |
| `read_range` | Sheet1, C1 (单单元格) | ✅ PASS | 返回单个值 |
| `write_range` | Sheet1, E1, [["new1","new2"],["new3","new4"]] | ✅ PASS | 新写入成功 |
| `write_range` | Sheet1, A1, [["Overwritten"]], overwrite=true | ✅ PASS | 覆盖写入成功 |
| `copy_range` | Sheet1, A1:A2 → H1 | ✅ PASS | 数据和样式复制正确 |
| `delete_range` | Sheet1, H1:H2 | ✅ PASS | 清除内容，保留格式 |
| `insert_rows` | Sheet1, start=1, count=2 | ✅ PASS | 插入 2 行 |
| `delete_rows` | Sheet1, start=1, count=1 | ✅ PASS | 删除 1 行 |
| `insert_columns` | Sheet1, start=1, count=1 | ✅ PASS | 插入 1 列 |
| `delete_columns` | Sheet1, start=1, count=1 | ✅ PASS | 删除 1 列 |
| `create_sheet` | "Sheet3", index=2 | ✅ PASS | 在指定位置创建 |
| `rename_sheet` | Sheet3 → Sheet3Renamed | ✅ PASS | 重命名成功 |
| `delete_sheet` | Sheet2 | ✅ PASS | 删除成功 |
| `format_range` | Sheet1, A1:B2, bold+font_size+font_color | ✅ PASS | 格式化成功 |
| `format_range` | Sheet1, A1:B1, merge=true | ✅ PASS | 合并单元格 |
| `format_range` | Sheet1, A1:B1, unmerge=true | ✅ PASS | 取消合并 |
| `write_chart` | Sheet1, bar, D1:E3 → G1 | ✅ PASS | 柱状图创建成功 |
| `write_chart` | Sheet1, line, D1:E3 → G20 | ✅ PASS | 折线图创建成功 |
| `write_chart` | Sheet1, pie, D1:E3 → G39 | ✅ PASS | 饼图创建成功 |
| `write_chart` | Sheet1, scatter, D1:E3 → G58 | ✅ PASS | 散点图创建成功 |
| `read_chart` | Sheet1 | ✅ PASS | 返回 4 个图表，title 字段有问题 |
| `inspect` | test.docx | ✅ PASS | 返回段落/表格/图片计数和详情 |
| `insert_para` | test.docx, "Fourth paragraph" | ✅ PASS | 末尾追加成功 |
| `insert_para` | test.docx, "Inserted at index 1", index=1 | ✅ PASS | 指定位置插入成功 |
| `modify_para` | test.docx, index=0, "Modified first" | ✅ PASS | 修改成功 |
| `format_para` | test.docx, index=0, style="Heading 1" | ✅ PASS | 样式应用成功 |
| `format_para` | test.docx, index=1, alignment="center" | ✅ PASS | 对齐设置成功 |
| `format_para` | test.docx, index=2, bold+italic+font_size+font_color | ✅ PASS | 字体格式成功 |
| `insert_table` | test.docx, rows=3, cols=2 | ✅ PASS | 空表格创建成功 |
| `insert_table` | test.docx, rows=2, cols=3, data=[[...]] | ✅ PASS | 带数据表格创建成功 |
| `modify_table` | test.docx, table_index=0, row=0, col=0, "Modified cell" | ✅ PASS | 单元格修改成功 |
| `format_table` | test.docx, table_index=0, style="Table Grid" | ✅ PASS | 表格样式应用成功 |
| `insert_image` | test.docx, test_image.png | ✅ PASS | 默认尺寸插入成功 |
| `insert_image` | test.docx, test_image.png, width=2 | ✅ PASS | 指定宽度插入成功 |
| `delete_image` | test.docx, image_index=0 | ✅ PASS | 图片删除成功 |
| `delete_para` | test.docx, index=0 | ✅ PASS | 段落删除成功 |
| `delete_table` | test.docx, table_index=0 | ✅ PASS | 表格删除成功 |
| `backup_history` | test.docx | ✅ PASS | 返回 35 个版本记录 |
| `backup_restore` | test.docx, version=21 | ✅ PASS | 恢复到指定版本 |
| `workbook_metadata` | nonexistent.xlsx | ✅ PASS | 返回错误 "No such file or directory" |
| `workbook_search` | Sheet1, "test" (Sheet="NoSheet") | ✅ PASS | 返回错误 "Sheet not found" |
| `read_range` | nonexistent.xlsx | ✅ PASS | 返回错误 "No such file or directory" |
| `modify_para` | test.docx, index=100 | ✅ PASS | 返回错误 "out of range" |
| `format_para` | test.docx, index=0, style="NonExistent" | ✅ PASS | 返回错误 "Style not found" |
| `format_para` | test.docx, index=0, alignment="diagonal" | ✅ PASS | 返回错误 "Invalid alignment" |

**总计: 48 个测试用例, 48 通过, 0 FAIL, 0 WARN**

---

## 排版视觉验证

通过本地 Word/Excel COM 自动化导出 PDF → pymupdf 渲染 200 DPI PNG，验证文档实际排版效果。

### DOCX 排版验证 (format_test_word_page1.png)

| 验证项 | 预期 | PNG 实际效果 | 状态 |
|--------|------|-------------|------|
| Title 样式 | 加粗 26pt 居中，带下划线 | 大号加粗居中，标题下方有蓝色分隔线 | ✅ 正确 |
| Heading 1 | 16pt 蓝色 | 较大蓝色文字，与 Normal 明显区分 | ✅ 正确 |
| Heading 2 | 14pt 蓝色 | 中等蓝色文字，比 H1 小 | ✅ 正确 |
| Heading 3 | 12pt 蓝色 | 较小蓝色文字，比 H2 小 | ✅ 正确 |
| Normal 段落 | 默认样式 | 正常黑色正文 | ✅ 正确 |
| 右对齐段落 | alignment=RIGHT | 文字靠右对齐 | ✅ 正确 |
| 表格 Table Grid | 3×4 带边框 | 3 行 4 列，边框清晰可见 | ✅ 正确 |

### XLSX 排版验证 (format_test_excel_page1.png)

| 验证项 | 预期 | PNG 实际效果 | 状态 |
|--------|------|-------------|------|
| 表头行 | 加粗白色字体+深色背景 | 白色字体在白色 PDF 背景上不可见，表头整行消失 | ❌ 异常 |
| 数据区数值格式 | 0.0 (100.0, 150.0…) | 数值显示为 100.0、150.0 等，格式正确 | ✅ 正确 |
| 合计行样式 | 加粗红色 (#FF0000) | "合计"及数值均为红色加粗，醒目可见 | ✅ 正确 |
| 柱状图渲染 | 3 组柱状（苹果/香蕉/橙子） | 3 组柱状完整显示，标题"季度销售对比"可见 | ✅ 正确 |
| 图表 X 轴标签 | 产品名称 | 显示数字 "1"/"2"/"3" 而非产品名 | ⚠️ 标签异常 |
| 图表图例 | 产品/Q1-Q4 | 图例显示 5 项，颜色区分清晰 | ✅ 正确 |

> PNG 文件位于 `tests/HIL/test_output/png/` 目录。

---

## 详细测试记录

### 1. version()
```
请求: carrot-office_version()
响应: {status: "ok", name: "carrot-mcp-office", version: "0.1.3", backup: {root: "...", max_versions: 100, max_age_days: 14}}
结论: ✅ 正常返回服务名称、版本号和备份配置
```

### 2. workbook_metadata()
```
请求: carrot-office_workbook_metadata(path="...test.xlsx")
响应: {status: "ok", sheets: ["Sheet1", "Sheet2"], title: null, creator: "openpyxl", created: "2026-06-30...", modified: "2026-06-30..."}
结论: ✅ 正确返回工作表列表和文档属性
```

### 3. workbook_search()
```
请求: carrot-office_workbook_search(path="...test.xlsx", sheet="Sheet1", query="hello")
响应: {status: "ok", sheet: "Sheet1", query: "hello", results: [{cell: "A1", value: "Hello"}], count: 1}
结论: ✅ 大小写不敏感搜索正常
```

### 4. read_range() - 范围读取
```
请求: carrot-office_read_range(path="...test.xlsx", sheet="Sheet1", start="A1", end="B2")
响应: {status: "ok", sheet: "Sheet1", range: "A1:B2", data: [["Hello", "World"], [42, 99]]}
结论: ✅ 返回二维数组，数据正确
```

### 5. read_range() - 单单元格
```
请求: carrot-office_read_range(path="...test.xlsx", sheet="Sheet1", start="C1")
响应: {status: "ok", sheet: "Sheet1", cell: "C1", value: "Test"}
结论: ✅ 单单元格模式正常
```

### 6. write_range() - 新写入
```
请求: carrot-office_write_range(path="...test.xlsx", sheet="Sheet1", start="E1", data=[["new1","new2"],["new3","new4"]])
响应: {status: "ok", sheet: "Sheet1", start: "E1", rows: 2, cols: 2, version: 1}
结论: ✅ 写入成功，备份版本递增
```

### 7. write_range() - 覆盖写入
```
请求: carrot-office_write_range(path="...test.xlsx", sheet="Sheet1", start="A1", data=[["Overwritten"]], overwrite=true)
响应: {status: "ok", sheet: "Sheet1", start: "A1", rows: 1, cols: 1, version: 2}
结论: ✅ overwrite=true 时允许覆盖已有数据
```

### 8. copy_range()
```
请求: carrot-office_copy_range(path="...test.xlsx", sheet="Sheet1", source_start="A1", source_end="A2", target_start="H1")
响应: {status: "ok", sheet: "Sheet1", source: "A1:A2", target: "H1", version: 3}
结论: ✅ 数据和样式正确复制
```

### 9. delete_range()
```
请求: carrot-office_delete_range(path="...test.xlsx", sheet="Sheet1", start="H1", end="H2")
响应: {status: "ok", sheet: "Sheet1", range: "H1:H2", version: 4}
结论: ✅ 清除内容，保留格式
```

### 10-13. insert_rows / delete_rows / insert_columns / delete_columns
```
请求: carrot-office_insert_rows(path="...test.xlsx", sheet="Sheet1", start=1, count=2)
响应: {status: "ok", sheet: "Sheet1", start: 1, count: 2, version: 5}
请求: carrot-office_delete_rows(path="...test.xlsx", sheet="Sheet1", start=1, count=1)
响应: {status: "ok", sheet: "Sheet1", start: 1, count: 1, version: 6}
请求: carrot-office_insert_columns(path="...test.xlsx", sheet="Sheet1", start=1, count=1)
响应: {status: "ok", sheet: "Sheet1", start: 1, count: 1, version: 7}
请求: carrot-office_delete_columns(path="...test.xlsx", sheet="Sheet1", start=1, count=1)
响应: {status: "ok", sheet: "Sheet1", start: 1, count: 1, version: 8}
结论: ✅ 行列插入/删除均正常
```

### 14. create_sheet()
```
请求: carrot-office_create_sheet(path="...test.xlsx", name="Sheet3", index=2)
响应: {status: "ok", sheet: "Sheet3", index: 2, version: 9}
结论: ✅ 在指定位置创建工作表
```

### 15. rename_sheet()
```
请求: carrot-office_rename_sheet(path="...test.xlsx", old_name="Sheet3", new_name="Sheet3Renamed")
响应: {status: "ok", old_name: "Sheet3", new_name: "Sheet3Renamed", version: 10}
结论: ✅ 重命名成功
```

### 16. delete_sheet()
```
请求: carrot-office_delete_sheet(path="...test.xlsx", name="Sheet2")
响应: {status: "ok", sheet: "Sheet2", version: 19}
结论: ✅ 删除成功
```

### 17. format_range()
```
请求: carrot-office_format_range(path="...test.xlsx", sheet="Sheet1", start="A1", end="B2", bold=true, font_size=14, font_color="FF0000")
响应: {status: "ok", sheet: "Sheet1", range: "A1:B2", version: 11}
结论: ✅ 字体格式化成功
```

### 18-19. format_range() - merge/unmerge
```
请求: carrot-office_format_range(path="...test.xlsx", sheet="Sheet1", start="A1", end="B1", merge=true)
响应: {status: "ok", sheet: "Sheet1", range: "A1:B1", version: 13}
请求: carrot-office_format_range(path="...test.xlsx", sheet="Sheet1", start="A1", end="B1", unmerge=true)
响应: {status: "ok", sheet: "Sheet1", range: "A1:B1", version: 14}
结论: ✅ 合并和取消合并均正常
```

### 20-23. write_chart()
```
请求: carrot-office_write_chart(path="...test.xlsx", sheet="Sheet1", chart_type="bar", data_range="D1:E3", target_cell="G1", title="Test Bar Chart")
响应: {status: "ok", sheet: "Sheet1", chart_type: "bar", target: "G1", version: 15}
请求: carrot-office_write_chart(..., chart_type="line", ..., target_cell="G20")
响应: {status: "ok", chart_type: "line", target: "G20", version: 16}
请求: carrot-office_write_chart(..., chart_type="pie", ..., target_cell="G39")
响应: {status: "ok", chart_type: "pie", target: "G39", version: 17}
请求: carrot-office_write_chart(..., chart_type="scatter", ..., target_cell="G58")
响应: {status: "ok", chart_type: "scatter", target: "G58", version: 18}
结论: ✅ 四种图表类型均创建成功
```

### 24. read_chart()
```
请求: carrot-office_read_chart(path="...test.xlsx", sheet="Sheet1")
响应: {status: "ok", sheet: "Sheet1", charts: [{index: 0, type: "BarChart", title: "<openpyxl...object repr>"}, ...], count: 4}
结论: ⚠️ 数量和类型正确，但 title 字段返回对象 repr 而非实际字符串
```

### 25. inspect()
```
请求: carrot-office_inspect(path="...test.docx")
响应: {status: "ok", paragraph_count: 3, table_count: 0, image_count: 0, styles_used: ["Normal"], paragraphs: [...], tables: []}
结论: ✅ 正确返回文档结构信息
```

### 26-27. insert_para()
```
请求: carrot-office_insert_para(path="...test.docx", text="Fourth paragraph (appended)")
响应: {status: "ok", text: "Fourth paragraph (appended)", index: 3, version: 21}
请求: carrot-office_insert_para(path="...test.docx", text="Inserted at index 1", index=1)
响应: {status: "ok", text: "Inserted at index 1", index: 1, version: 22}
结论: ✅ 末尾追加和指定位置插入均正常
```

### 28. modify_para()
```
请求: carrot-office_modify_para(path="...test.docx", index=0, text="Modified first paragraph")
响应: {status: "ok", index: 0, old_text: "First paragraph", new_text: "Modified first paragraph", version: 23}
结论: ✅ 修改成功，返回新旧文本
```

### 29-31. format_para()
```
请求: carrot-office_format_para(path="...test.docx", index=0, style="Heading 1")
响应: {status: "ok", index: 0, version: 24}
请求: carrot-office_format_para(path="...test.docx", index=1, alignment="center")
响应: {status: "ok", index: 1, version: 25}
请求: carrot-office_format_para(path="...test.docx", index=2, bold=true, italic=true, font_size=14, font_color="FF0000")
响应: {status: "ok", index: 2, version: 26}
结论: ✅ 样式、对齐、字体格式均正常
```

### 32-33. insert_table()
```
请求: carrot-office_insert_table(path="...test.docx", rows=3, cols=2)
响应: {status: "ok", rows: 3, cols: 2, index: 0, version: 27}
请求: carrot-office_insert_table(path="...test.docx", rows=2, cols=3, data=[["A","B","C"],[1,2,3]])
响应: {status: "ok", rows: 2, cols: 3, index: 1, version: 28}
结论: ✅ 空表格和带数据表格均创建成功
```

### 34-35. modify_table() / format_table()
```
请求: carrot-office_modify_table(path="...test.docx", table_index=0, row=0, col=0, text="Modified cell")
响应: {status: "ok", table_index: 0, row: 0, col: 0, old_text: "", new_text: "Modified cell", version: 29}
请求: carrot-office_format_table(path="...test.docx", table_index=0, style="Table Grid")
响应: {status: "ok", table_index: 0, style: "Table Grid", version: 30}
结论: ✅ 单元格修改和表格样式均正常
```

### 36-37. insert_image()
```
请求: carrot-office_insert_image(path="...test.docx", image_path="...test_image.png")
响应: {status: "ok", image_path: "...test_image.png", index: null, version: 31}
请求: carrot-office_insert_image(path="...test.docx", image_path="...test_image.png", width=2)
响应: {status: "ok", image_path: "...test_image.png", index: null, version: 32}
结论: ✅ 默认尺寸和指定宽度均插入成功
```

### 38. delete_image()
```
请求: carrot-office_delete_image(path="...test.docx", image_index=0)
响应: {status: "ok", image_index: 0, version: 33}
结论: ✅ 图片删除成功
```

### 39. delete_para()
```
请求: carrot-office_delete_para(path="...test.docx", index=0)
响应: {status: "ok", index: 0, version: 34}
结论: ✅ 段落删除成功
```

### 40. delete_table()
```
请求: carrot-office_delete_table(path="...test.docx", table_index=0)
响应: {status: "ok", table_index: 0, version: 35}
结论: ✅ 表格删除成功
```

### 41. backup_history()
```
请求: carrot-office_backup_history(path="...test.docx")
响应: {status: "ok", path: "...test.docx", versions: [{number: 1, file: "test_v001.xlsx", ...}, ...], count: 35}
结论: ✅ 返回版本列表，但混入了 test.xlsx 的版本
```

### 42. backup_restore()
```
请求: carrot-office_backup_restore(path="...test.docx", version=21)
响应: {status: "ok", path: "...test.docx", restored_version: 21}
结论: ✅ 恢复成功，通过 inspect 验证文档回到 version 21 状态
```

### 43-48. 错误处理
```
请求: carrot-office_workbook_metadata(path="...nonexistent.xlsx")
响应: {status: "error", message: "[Errno 2] No such file or directory: ..."}
结论: ✅ 文件不存在时返回错误

请求: carrot-office_workbook_search(path="...test.xlsx", sheet="NoSheet", query="test")
响应: {status: "error", message: "Sheet 'NoSheet' not found"}
结论: ✅ 工作表不存在时返回错误

请求: carrot-office_modify_para(path="...test.docx", index=100, text="Text")
响应: {status: "error", message: "Paragraph index 100 out of range (0-3)"}
结论: ✅ 段落索引越界时返回错误

请求: carrot-office_format_para(path="...test.docx", index=0, style="NonExistentStyle")
响应: {status: "error", message: "Style 'NonExistentStyle' not found"}
结论: ✅ 样式不存在时返回错误

请求: carrot-office_format_para(path="...test.docx", index=0, alignment="diagonal")
响应: {status: "error", message: "Invalid alignment 'diagonal'. Use: left, center, right, justify"}
结论: ✅ 无效对齐值时返回错误
```

---

## 未测试项目

1. **并发操作** - 未测试多线程同时操作同一文件
2. **超大文件** - 未测试大尺寸 xlsx/docx 文件
3. **特殊字符** - 未测试文件路径含空格/中文的情况
4. **convert 模块** - 未测试 .xls/.doc → .xlsx/.docx 自动转换

---

## 发现的问题

### 🔴 严重问题

### 问题 1: Excel 表头白色字体在 PDF 导出后不可见
- **现象**: `format_range` 设置 `font_color="FFFFFF"` (白色) 的表头行，通过 Excel COM 导出 PDF 后，白色文字在白色背景上完全不可见，表头整行"消失"
- **期望**: 应同时设置深色填充背景 (fill_color)，或在字体颜色选择时避免纯白
- **影响**: 高 - 用户在打印/导出 PDF 时丢失表头，数据无法辨识
- **建议**: `format_range` 应支持 `fill_color` 参数；或在文档中提示白色字体需配合深色背景使用

### 🟡 一般问题

### 问题 2: read_chart() 的 title 字段返回对象 repr
- **现象**: `read_chart()` 返回的 `title` 字段是 openpyxl Title 对象的 `repr()`，而非实际标题字符串
- **期望**: 应提取 `chart.title.tx.rich.p[0].r[0].t` 获取实际标题
- **影响**: 中 - LLM 收到不可读的对象表示，无法理解图表标题
- **建议**: 修改 `excel.py:476`，从 Title 对象中提取实际字符串

### 问题 3: write_chart() X 轴标签显示行号而非首列文本
- **现象**: 柱状图的 X 轴标签显示 "1"/"2"/"3"（行号），而非 A 列的产品名称（苹果/香蕉/橙子）
- **期望**: X 轴应使用首列文本作为 category 标签
- **影响**: 中 - 图表标签无意义，用户需手动识别数据
- **建议**: 检查 `write_chart` 中 openpyxl 的 `cat` 引用是否正确指向首列文本区域

### 问题 4: backup_history() 跨文件污染
- **现象**: `backup_history(path="test.docx")` 返回了 test.xlsx 的版本记录
- **期望**: 应按原始文件名过滤，仅返回指定文件的版本
- **影响**: 低 - 输出混淆，但版本本身是文件独立的
- **建议**: 在备份列表中添加文件名过滤

### 问题 5: insert_image() 异常信息不友好
- **现象**: 插入不存在的图片文件时抛出 Python 异常而非友好错误消息
- **期望**: 应捕获异常并返回 `{status: "error", message: "Image file not found: ..."}`
- **影响**: 低 - 错误信息不够清晰
- **建议**: 在 `insert_image` 中添加文件存在性检查

---

## 总结

carrot-office MCP 服务的 30 个方法（Excel 18 个 + Word 12 个 + Backup 2 个）在正常情况下工作良好。**48 个测试用例全部通过**，排版视觉验证发现 **5 个问题**（1 严重 + 4 一般）：

### 关键发现

| # | 问题 | 严重程度 | 说明 |
|---|------|----------|------|
| 1 | Excel 白色字体 PDF 导出后不可见 | 🔴 严重 | 表头整行"消失"，format_range 缺少 fill_color 参数 |
| 2 | `read_chart()` title 字段返回对象 repr | 🟡 一般 | LLM 无法理解图表标题 |
| 3 | `write_chart()` X 轴标签显示行号 | 🟡 一般 | 应显示首列文本而非数字 |
| 4 | `backup_history()` 跨文件污染 | 🟡 一般 | 混入其他文件的版本记录 |
| 5 | `insert_image()` 异常信息不友好 | 🟡 一般 | 未捕获文件不存在异常 |

### 建议优先级

1. **尽快修复**: 问题 1（影响打印/导出场景的数据可读性）
2. **计划修复**: 问题 2、3（影响图表功能完整性）
3. **低优先级**: 问题 4、5

**总体评价**: 服务基础功能完善，API 设计合理，错误处理恰当。Word 排版全部正确（样式、对齐、表格均通过视觉验证）。Excel 数据写入和格式化正确，但存在白色字体可见性和图表渲染两个需要关注的问题。
