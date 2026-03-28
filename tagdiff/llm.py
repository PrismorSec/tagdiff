import json
import os

from tagdiff.config import DEFAULT_MODEL


def _get_model(model=None):
    return model or DEFAULT_MODEL


def generate_structured_changelog(changelog_text, model=None):
    try:
        from litellm import completion
    except ImportError:
        return {"error": "litellm package missing. Install it with 'pip install litellm'"}

    prompt = """
    You are a changelog assistant.
    Extract the following from the changelog text:
    - breaking_changes (list of strings)
    - features (list of strings)
    - fixes (list of strings)
    - deprecations (list of strings)
    - other (list of strings)

    Return ONLY JSON. Do not use markdown blocks.
    """

    try:
        response = completion(
            model=_get_model(model),
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": changelog_text},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        return {"error": str(e)}


def stream_analysis(system_prompt, user_content, model=None):
    """Stream an LLM completion and return the full text."""
    from litellm import completion

    response = completion(
        model=_get_model(model),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        stream=True,
    )
    print()

    full_response = []
    for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            print(delta.content, end="", flush=True)
            full_response.append(delta.content)

    print()
    return "".join(full_response)
