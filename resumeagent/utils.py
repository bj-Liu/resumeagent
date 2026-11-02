from yaspin import yaspin


def user_message(prompt: str, images=()) -> list[dict]:
    """Build the shared image-first multimodal user message format."""
    content = [{'type': 'image', 'url': image} for image in images]
    content.append({'type': 'text', 'text': prompt})
    return [{'role': 'user', 'content': content}]


def format_profile(profile) -> str:
    """Keep the profile labels and whitespace used by existing business prompts."""
    basic_information = profile.get('basic_information', '')
    academic_achievements = profile.get('academic_achievements', '')
    experience = profile.get('experience', '')
    professional_skills = profile.get('professional_skills', '')
    return (
        f'Basic Information: {basic_information}\n'
        f'academic_achievements: {academic_achievements}\n'
        f'Experience: {experience}\n'
        f'Professional Skills: {professional_skills}'
    )


def cal_cost(prompt_tokens, completion_tokens, model="qwen3.8-2.4t-a95b"):
    if "gpt-4o" in model:
        return prompt_tokens / 1000000 * 5 + completion_tokens / 1000000 * 15

    elif "Sonnet" in model:
        return prompt_tokens / 1000000 * 3 + completion_tokens / 1000000 * 15

    elif model == "qwen3.8-max":
        return prompt_tokens / 1000000 * 12 + completion_tokens / 1000000 * 36

    elif model == "qwen3.8-flash":
        # CNY per million tokens for the configured Beijing/global deployment.
        return prompt_tokens / 1000000 * 0.8 + completion_tokens / 1000000 * 2.7
    elif model == "qwen3.8-2.4t-a95b":
        # CNY per million tokens for the configured Beijing/global deployment.
        return prompt_tokens / 1000000 * 3 + completion_tokens / 1000000 * 12
    elif model == "qwen3.8-omni-flash":
        # CNY per million tokens for the configured Beijing/global deployment.
        return prompt_tokens / 1000000 * 0.8 + completion_tokens / 1000000 * 2.7
    else:
        return prompt_tokens / 1000 * 0.005 + completion_tokens / 1000 * 0.015



def get_content_between_a_b(start_tag, end_tag, text):
    extracted_text = ""
    start_index = text.find(start_tag)
    while start_index != -1:
        end_index = text.find(end_tag, start_index + len(start_tag))
        if end_index != -1:
            extracted_text += text[start_index + len(start_tag) : end_index] + " "
            start_index = text.find(start_tag, end_index + len(end_tag))
        else:
            break

    return extracted_text.strip()


def extract(text, type):
    target_str = get_content_between_a_b(f"<{type}>", f"</{type}>", text)
    return target_str





def wrap_func(func,**args):
    text = "🤖💭 " + args.get("wrap_text","Thinking now...")
    if "wrap_text" in args:
        del args["wrap_text"]
    import sys
    if not sys.stdout.isatty():
        return func(**args)
    with yaspin(text = text, color="cyan") as spinner:
        result = func(**args)
        spinner.ok("✔")
    return result







def modify_input_dict(s):
    s = s.replace("\'","\"")
    s = s.replace("False","false")
    s = s.replace("True","true")
    s = s.replace("None","null")
    s = s.replace("\'","\"")
    s = s.replace("\"s","\'s")
    s = s.replace(" \'"," \"")
    return s

def get_html_css_from_response(response):
    html = get_content_between_a_b("```html", "```", response) if "```html" in response else None
    css = get_content_between_a_b("```css", "```", response) if "```css" in response else None
    return html,css
