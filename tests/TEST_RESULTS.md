# TEXT_BOX API Test Results

**Date**: 2026-01-11 14:45:37
**Endpoint**: https://web-production-5daf.up.railway.app/v1.2/atomic/TEXT_BOX
**Total Tests**: 22 | **Passed**: 22 | **Failed**: 0

---

## Summary Table

| # | Test Name | Status | Time (ms) | HTML Chars | Instances | Arrangement |
|---|-----------|--------|-----------|------------|-----------|-------------|
| 1 | Default Config | PASS | 188 | 3200 | 3 | row_3 |
| 2 | Numbers List | PASS | 35 | 3131 | 3 | row_3 |
| 3 | Plain Text | PASS | 37 | 3860 | 3 | row_3 |
| 4 | Transparent BG | PASS | 30 | 3200 | 3 | row_3 |
| 5 | Square Corners | PASS | 33 | 3200 | 3 | row_3 |
| 6 | With Border | PASS | 34 | 3200 | 3 | row_3 |
| 7 | Solid Colors | PASS | 31 | 3200 | 3 | row_3 |
| 8 | Accent Light | PASS | 35 | 3200 | 3 | row_3 |
| 9 | Accent Dark | PASS | 35 | 3124 | 3 | row_3 |
| 10 | Vertical Layout | PASS | 42 | 3200 | 3 | stacked_3 |
| 11 | Grid Layout | PASS | 30 | 3200 | 3 | grid_1x3 |
| 12 | Center Aligned | PASS | 32 | 3212 | 3 | row_3 |
| 13 | Right Aligned | PASS | 32 | 3206 | 3 | row_3 |
| 14 | No Title | PASS | 25 | 3200 | 3 | row_3 |
| 15 | Max Items | PASS | 32 | 4406 | 3 | row_3 |
| 16 | Single Box | PASS | 34 | 1161 | 1 | row_1 |
| 17 | Complex: Num+Vert+Border | PASS | 32 | 3143 | 3 | stacked_3 |
| 18 | Complex: None+Grid+Accent | PASS | 31 | 3784 | 3 | grid_1x3 |
| 19 | Complex: All Options | PASS | 33 | 3061 | 3 | grid_1x3 |
| 20 | Title: Highlighted | PASS | 34 | 3200 | 3 | row_3 |
| 21 | Title: Colored Badge | PASS | 5884 | 2938 | 3 | row_3 |
| 22 | Title: Badge + Accent | PASS | 5031 | 2870 | 3 | row_3 |

---

## Detailed Results

### Test 1: Default Config

- **Status**: PASS
- **Description**: Baseline test with all default values
- **Response Time**: 188ms
- **HTML Characters**: 3200
- **Instance Count**: 3
- **Arrangement**: row_3
- **Config**: list_style=bullets, background_style=colored, corners=rounded, border=False, color_scheme=gradient, layout=horizontal, theme_mode=light, heading_align=left, content_align=left, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Lorem ipsum dolor sit amet consectetur</h3><ul style="list-style-type: disc; margin: 0; padding-
```

### Test 2: Numbers List

- **Status**: PASS
- **Description**: Numbered items instead of bullets
- **Response Time**: 35ms
- **HTML Characters**: 3131
- **Instance Count**: 3
- **Arrangement**: row_3
- **Config**: list_style=numbers, background_style=colored, corners=rounded, border=False, color_scheme=gradient, layout=horizontal, theme_mode=light, heading_align=left, content_align=left, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Lorem ipsum dolor sit amet consectetur</h3><ol style="margin: 0; padding-left: 24px; font-size: 
```

### Test 3: Plain Text

- **Status**: PASS
- **Description**: No list markers (paragraphs)
- **Response Time**: 37ms
- **HTML Characters**: 3860
- **Instance Count**: 3
- **Arrangement**: row_3
- **Config**: list_style=none, background_style=colored, corners=rounded, border=False, color_scheme=gradient, layout=horizontal, theme_mode=light, heading_align=left, content_align=left, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Lorem ipsum dolor sit amet consectetur</h3><div style="margin: 0;"><p style="margin: 0 0 12px 0;
```

### Test 4: Transparent BG

- **Status**: PASS
- **Description**: Transparent background instead of colored
- **Response Time**: 30ms
- **HTML Characters**: 3200
- **Instance Count**: 3
- **Arrangement**: row_3
- **Config**: list_style=bullets, background_style=transparent, corners=rounded, border=False, color_scheme=gradient, layout=horizontal, theme_mode=light, heading_align=left, content_align=left, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Lorem ipsum dolor sit amet consectetur</h3><ul style="list-style-type: disc; margin: 0; padding-
```

### Test 5: Square Corners

- **Status**: PASS
- **Description**: Sharp square corners instead of rounded
- **Response Time**: 33ms
- **HTML Characters**: 3200
- **Instance Count**: 3
- **Arrangement**: row_3
- **Config**: list_style=bullets, background_style=colored, corners=square, border=False, color_scheme=gradient, layout=horizontal, theme_mode=light, heading_align=left, content_align=left, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Lorem ipsum dolor sit amet consectetur</h3><ul style="list-style-type: disc; margin: 0; padding-
```

### Test 6: With Border

- **Status**: PASS
- **Description**: Border enabled around boxes
- **Response Time**: 34ms
- **HTML Characters**: 3200
- **Instance Count**: 3
- **Arrangement**: row_3
- **Config**: list_style=bullets, background_style=transparent, corners=rounded, border=True, color_scheme=gradient, layout=horizontal, theme_mode=light, heading_align=left, content_align=left, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Lorem ipsum dolor sit amet consectetur</h3><ul style="list-style-type: disc; margin: 0; padding-
```

### Test 7: Solid Colors

- **Status**: PASS
- **Description**: Solid color scheme instead of gradient
- **Response Time**: 31ms
- **HTML Characters**: 3200
- **Instance Count**: 3
- **Arrangement**: row_3
- **Config**: list_style=bullets, background_style=colored, corners=rounded, border=False, color_scheme=solid, layout=horizontal, theme_mode=light, heading_align=left, content_align=left, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Lorem ipsum dolor sit amet consectetur</h3><ul style="list-style-type: disc; margin: 0; padding-
```

### Test 8: Accent Light

- **Status**: PASS
- **Description**: Accent color scheme with light theme mode
- **Response Time**: 35ms
- **HTML Characters**: 3200
- **Instance Count**: 3
- **Arrangement**: row_3
- **Config**: list_style=bullets, background_style=transparent, corners=rounded, border=False, color_scheme=accent, layout=horizontal, theme_mode=light, heading_align=left, content_align=left, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Lorem ipsum dolor sit amet consectetur</h3><ul style="list-style-type: disc; margin: 0; padding-
```

### Test 9: Accent Dark

- **Status**: PASS
- **Description**: Accent color scheme with dark theme mode
- **Response Time**: 35ms
- **HTML Characters**: 3124
- **Instance Count**: 3
- **Arrangement**: row_3
- **Config**: list_style=bullets, background_style=transparent, corners=rounded, border=False, color_scheme=accent, layout=horizontal, theme_mode=dark, heading_align=left, content_align=left, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: #E6D2F5; margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Lorem ipsum dolor sit amet consectetur</h3><ul style="list-style-type: disc; margin: 0; padding-left: 20px; font-size: 21px
```

### Test 10: Vertical Layout

- **Status**: PASS
- **Description**: Stacked vertical layout
- **Response Time**: 42ms
- **HTML Characters**: 3200
- **Instance Count**: 3
- **Arrangement**: stacked_3
- **Config**: list_style=bullets, background_style=colored, corners=rounded, border=False, color_scheme=gradient, layout=vertical, theme_mode=light, heading_align=left, content_align=left, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(1, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Lorem ipsum dolor sit amet consectetur</h3><ul style="list-style-type: disc; margin: 0; padding-
```

### Test 11: Grid Layout

- **Status**: PASS
- **Description**: 2x2 grid layout
- **Response Time**: 30ms
- **HTML Characters**: 3200
- **Instance Count**: 3
- **Arrangement**: grid_1x3
- **Config**: list_style=bullets, background_style=colored, corners=rounded, border=False, color_scheme=gradient, layout=grid, theme_mode=light, heading_align=left, content_align=left, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Lorem ipsum dolor sit amet consectetur</h3><ul style="list-style-type: disc; margin: 0; padding-
```

### Test 12: Center Aligned

- **Status**: PASS
- **Description**: Center aligned heading and content
- **Response Time**: 32ms
- **HTML Characters**: 3212
- **Instance Count**: 3
- **Arrangement**: row_3
- **Config**: list_style=bullets, background_style=colored, corners=rounded, border=False, color_scheme=gradient, layout=horizontal, theme_mode=light, heading_align=center, content_align=center, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: center;">Lorem ipsum dolor sit amet consectetur</h3><ul style="list-style-type: disc; margin: 0; paddin
```

### Test 13: Right Aligned

- **Status**: PASS
- **Description**: Right aligned heading and content
- **Response Time**: 32ms
- **HTML Characters**: 3206
- **Instance Count**: 3
- **Arrangement**: row_3
- **Config**: list_style=bullets, background_style=colored, corners=rounded, border=False, color_scheme=gradient, layout=horizontal, theme_mode=light, heading_align=right, content_align=right, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: right;">Lorem ipsum dolor sit amet consectetur</h3><ul style="list-style-type: disc; margin: 0; padding
```

### Test 14: No Title

- **Status**: PASS
- **Description**: Title hidden (show_title=false)
- **Response Time**: 25ms
- **HTML Characters**: 3200
- **Instance Count**: 3
- **Arrangement**: row_3
- **Config**: list_style=bullets, background_style=colored, corners=rounded, border=False, color_scheme=gradient, layout=horizontal, theme_mode=light, heading_align=left, content_align=left, show_title=False, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Lorem ipsum dolor sit amet consectetur</h3><ul style="list-style-type: disc; margin: 0; padding-
```

### Test 15: Max Items

- **Status**: PASS
- **Description**: Maximum 7 items per box
- **Response Time**: 32ms
- **HTML Characters**: 4406
- **Instance Count**: 3
- **Arrangement**: row_3
- **Config**: list_style=bullets, background_style=colored, corners=rounded, border=False, color_scheme=gradient, layout=horizontal, theme_mode=light, heading_align=left, content_align=left, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Lorem ipsum dolor sit amet consectetur</h3><ul style="list-style-type: disc; margin: 0; padding-
```

### Test 16: Single Box

- **Status**: PASS
- **Description**: Only 1 text box (count=1)
- **Response Time**: 34ms
- **HTML Characters**: 1161
- **Instance Count**: 1
- **Arrangement**: row_1
- **Config**: list_style=bullets, background_style=colored, corners=rounded, border=False, color_scheme=gradient, layout=horizontal, theme_mode=light, heading_align=left, content_align=left, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(1, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Lorem ipsum dolor sit amet consectetur</h3><ul style="list-style-type: disc; margin: 0; padding-
```

### Test 17: Complex: Num+Vert+Border

- **Status**: PASS
- **Description**: Numbers, vertical, square, border, solid, center
- **Response Time**: 32ms
- **HTML Characters**: 3143
- **Instance Count**: 3
- **Arrangement**: stacked_3
- **Config**: list_style=numbers, background_style=transparent, corners=square, border=True, color_scheme=solid, layout=vertical, theme_mode=light, heading_align=center, content_align=center, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(1, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: center;">Lorem ipsum dolor sit amet consectetur</h3><ol style="margin: 0; padding-left: 24px; font-size
```

### Test 18: Complex: None+Grid+Accent

- **Status**: PASS
- **Description**: No list, grid layout, accent, dark mode
- **Response Time**: 31ms
- **HTML Characters**: 3784
- **Instance Count**: 3
- **Arrangement**: grid_1x3
- **Config**: list_style=none, background_style=transparent, corners=rounded, border=False, color_scheme=accent, layout=grid, theme_mode=dark, heading_align=left, content_align=left, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: #E6D2F5; margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Lorem ipsum dolor sit amet consectetur</h3><div style="margin: 0;"><p style="margin: 0 0 12px 0; font-size: 21px; line-heig
```

### Test 19: Complex: All Options

- **Status**: PASS
- **Description**: Maximum variation test
- **Response Time**: 33ms
- **HTML Characters**: 3061
- **Instance Count**: 3
- **Arrangement**: grid_1x3
- **Config**: list_style=numbers, background_style=colored, corners=square, border=True, color_scheme=solid, layout=grid, theme_mode=dark, heading_align=right, content_align=right, show_title=True, title_style=plain

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: #E6D2F5; margin: 0 0 16px 0; line-height: 1.2; text-align: right;">Lorem ipsum dolor sit amet consectetur</h3><ol style="margin: 0; padding-left: 24px; font-size: 21px; line-height: 1.5; co
```

### Test 20: Title: Highlighted

- **Status**: PASS
- **Description**: Highlighted title style (bold, larger)
- **Response Time**: 34ms
- **HTML Characters**: 3200
- **Instance Count**: 3
- **Arrangement**: row_3
- **Config**: list_style=bullets, background_style=colored, corners=rounded, border=False, color_scheme=gradient, layout=horizontal, theme_mode=light, heading_align=left, content_align=left, show_title=True, title_style=highlighted

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Lorem ipsum dolor sit amet consectetur</h3><ul style="list-style-type: disc; margin: 0; padding-
```

### Test 21: Title: Colored Badge

- **Status**: PASS
- **Description**: Title in colored badge/pill (LLM mode)
- **Response Time**: 5884ms
- **HTML Characters**: 2938
- **Instance Count**: 3
- **Arrangement**: row_3
- **Config**: list_style=bullets, background_style=colored, corners=rounded, border=False, color_scheme=gradient, layout=horizontal, theme_mode=light, heading_align=left, content_align=left, show_title=True, title_style=colored-bg

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Code Quality & Maintainability</h3><ul style="list-style-type: disc; margin: 0; padding-left: 20
```

### Test 22: Title: Badge + Accent

- **Status**: PASS
- **Description**: Colored badge title with accent scheme (LLM mode)
- **Response Time**: 5031ms
- **HTML Characters**: 2870
- **Instance Count**: 3
- **Arrangement**: row_3
- **Config**: list_style=bullets, background_style=transparent, corners=rounded, border=False, color_scheme=accent, layout=horizontal, theme_mode=light, heading_align=left, content_align=left, show_title=True, title_style=colored-bg

**HTML Preview** (first 500 chars):
```html
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding: 0; align-items: start; height: fit-content;"><div style="padding: 24px; background: rgba(232, 215, 241, 0.6); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1);"><h3 style="font-size: 28px; font-weight: 700; color: var(--accent-text-purple, #805AA0); margin: 0 0 16px 0; line-height: 1.2; text-align: left;">Clean Code Principles</h3><ul style="list-style-type: disc; margin: 0; padding-left: 20px; font-
```
