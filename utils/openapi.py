import os
from typing import Optional
from openai import OpenAI
from config import config

def rewrite_html_direct(
    html_content: str,
    api_key: Optional[str] = None,
    model: str = "",
    temperature: float = 0.7,
) -> str:
    """
    直接将整个 HTML 字符串发给 DeepSeek，要求模型保留所有标签并同义替换文本内容。

    Args:
        html_content: 完整的 HTML 字符串（可含英、葡等语言）
        api_key: DeepSeek API Key（不传则从环境变量读取）
        model: 模型名称
        temperature: 生成温度（0~1）

    Returns:
        模型返回的 HTML 字符串（理论上标签结构不变，文本被改写）

    Raises:
        Exception: API 调用失败或返回内容异常
    """
    # 初始化客户端
    client = OpenAI(
        api_key=config.get("api_key") if not api_key else api_key,
        base_url=config.get("base_url")
    )

    if not model:
        model = config.get("model")
    if api_key:
        client.api_key = api_key
    elif not client.api_key:
        raise ValueError("请提供 DeepSeek API Key 或设置环境变量 DEEPSEEK_API_KEY")

    # 关键：系统提示 + 用户提示
    system_prompt = (
        "You are an HTML text rewriter. "
        "Your task: rewrite ONLY the visible text content inside the given HTML code, "
        "while keeping ALL HTML tags, attributes, and structure exactly the same. "
        "Do not change any tag names, class names, ids, or any angle-bracket syntax. "
        "Perform synonym replacement and slight rephrasing on the text content only. "
        "Preserve the original meaning and language (English/Portuguese). "
        "Output ONLY the rewritten HTML code, without any extra explanation or markdown formatting."
    )

    user_prompt = f"Rewrite the text content in this HTML:\n\n{html_content}"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max(4096, len(html_content) * 2),  # 预估输出 tokens
        )
        result = response.choices[0].message.content.strip()
        # 模型有时会输出 markdown 代码块，需要剥离
        if result.startswith("```html"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        return result.strip()
    except Exception as e:
        raise Exception(f"DeepSeek API 调用失败: {e}")

# ========== 使用示例 ==========
if __name__ == "__main__":
    sample_html = """
    <div class="content">
        <h1>Hello, this is a test</h1>
        <p>We need to rewrite this paragraph while keeping <strong>HTML tags</strong> intact.</p>
        <p>Este é um parágrafo em português para ser reescrito.</p>
    </div>
    """
    try:
        rewritten = rewrite_html_direct(sample_html)
        print("改写后的 HTML：\n", rewritten)
    except Exception as e:
        print("错误：", e)