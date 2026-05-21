<!-- === VISION_SKILL_START === -->

# Claude Code 视觉检查配置

## 前端页面检查流程（强制）

检查前端页面布局 / UI 时，**禁止**逐行阅读代码来推断布局问题，必须用截图 + 视觉模型分析实际渲染：

1. 确保 dev server 已启动，获取页面 URL
2. 用 `browser-harness` 截图：
   - `new_tab(url)` 打开页面
   - `wait_for_load()` 等待加载
   - `time.sleep(2)` 等待动画/渲染完成
   - `capture_screenshot` 全页截图
   - 滚动到不同位置再截 2-3 张，覆盖全部内容
3. 每张截图用 vision skill 分析：
   ```
   python ~/.claude/skills/vision/vision.py "截图路径" "分析布局问题：对齐、间距、溢出、留白、截断、空白区域等"
   ```
   可选 `--provider qwen` 或 `--provider openai` 切换模型
4. 输出乱码时用 GBK 解码：`open(path, 'rb').read().decode('gbk')`
5. 汇总所有截图的分析结果，列出完整的问题清单

<!-- === VISION_SKILL_END === -->
