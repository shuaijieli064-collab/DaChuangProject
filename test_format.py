# Test formatContent with real AI output

import re

# Simulated AI output from generate-questions endpoint
test_input = """根据提供的内容，以下是5道单选题：

## 题目1
**以下哪个是Python的主要特点？**

A. 编译型语言
B. 解释型语言
C. 汇编语言
D. 机器语言

**答案：B**

解析：Python是一种解释型语言，代码会被解释器逐行执行。

---

## 题目2
**已知函数 $f(x) = x^2 + 2x + 1$，则 $f(1)$ 的值为？**

A. $1$
B. $2$
C. $3$
D. $4$

**答案：D**

解析：$f(1) = 1^2 + 2 \times 1 + 1 = 1 + 2 + 1 = 4$

---

## 题目3
**求导数：若 $y = 3x^2 + 2x$，则 $\frac{dy}{dx} = $？**

A. $6x + 2$
B. $3x + 2$
C. $6x^2 + 2$
D. $3x^2$

**答案：A**

解析：根据幂函数求导法则，$\frac{d}{dx}(x^n) = nx^{n-1}$

$$\frac{d}{dx}(3x^2 + 2x) = 3 \times 2x^{2-1} + 2 \times 1x^{1-1} = 6x + 2$$
"""

def format_content(text):
    placeholders = []
    ph_idx = 0

    def make_ph(ctype, content):
        nonlocal ph_idx
        ph = f"%%PH_{ctype}_{ph_idx}%%"
        placeholders.append({"type": ctype, "content": content, "ph": ph})
        ph_idx += 1
        return ph

    # Step 1: Protect code blocks
    text = re.sub(r'```(\w*)\n([\s\S]*?)```', lambda m: make_ph('code', {'lang': m.group(1), 'code': m.group(2)}), text)

    # Step 2: Protect display math
    text = re.sub(r'\$\$([\s\S]*?)\$\$', lambda m: make_ph('displayMath', m.group(1)), text)

    # Step 3: Protect inline math
    text = re.sub(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', lambda m: make_ph('inlineMath', m.group(1)), text)

    # Step 4: HTML escape
    html = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # Step 5: Markdown
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\n', '<br>', html)

    # Step 6: Restore placeholders
    for item in placeholders:
        if item['type'] == 'code':
            rendered = f'<pre><code>{item["content"]["code"]}</code></pre>'
        elif item['type'] == 'displayMath':
            rendered = f'[MATH_DISPLAY]{item["content"]}[/MATH_DISPLAY]'
        else:
            rendered = f'[MATH_INLINE]{item["content"]}[/MATH_INLINE]'
        html = html.replace(item['ph'], rendered)

    return html

result = format_content(test_input)

# Show the result
for line in result.split('<br>'):
    print(line)
    print()
