<!-- === VISION_SKILL_START === -->

# Claude Code 视觉检查配置

## 前端页面检查流程（强制）

检查前端页面布局 / UI 时，**禁止**仅凭阅读代码推断布局问题，必须实际查看渲染截图：

1. 确保 dev server 已启动，获取页面 URL
2. 用 `browser-harness` 截图：
   - `new_tab(url)` 打开页面
   - `wait_for_load()` 等待加载
   - `time.sleep(2)` 等待动画/渲染完成
   - `capture_screenshot` 全页截图
   - 滚动到不同位置再截 2-3 张，覆盖全部内容
3. 分析每张截图的布局问题：对齐、间距、溢出、留白、截断、空白区域等。
   若你无法直接理解截图内容，必须使用可用的图像理解工具处理后再继续分析。
4. 输出乱码时用 GBK 解码：`open(path, 'rb').read().decode('gbk')`
5. 汇总所有截图的分析结果，列出完整的问题清单

<!-- === VISION_SKILL_END === -->
