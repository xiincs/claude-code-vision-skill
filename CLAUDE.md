<!-- === VISION_SKILL_START === -->

# Claude Code Visual Inspection Configuration

## Front-end Page Check Workflow (mandatory)

When checking front-end page layout / UI, **do not** infer layout problems merely by reading code — you must actually look at the rendered screenshot:

1. Make sure the dev server is running, and get the page URL
2. Take a screenshot with `browser-harness`:
   - `new_tab(url)` to open the page
   - `wait_for_load()` to wait for loading
   - `time.sleep(2)` to wait for animations/rendering to finish
   - `capture_screenshot` for a full-page screenshot
   - Scroll to different positions and capture 2-3 more screenshots to cover all content
3. Analyze each screenshot for layout issues: alignment, spacing, overflow, whitespace, truncation, empty areas, etc.
   If you cannot understand the screenshot content directly, you must process it with an available image-understanding tool before continuing the analysis.
4. If the output is garbled, decode as GBK: `open(path, 'rb').read().decode('gbk')`
5. Summarize the analysis results from all screenshots and list the complete set of issues

<!-- === VISION_SKILL_END === -->
