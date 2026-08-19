from backend.core import prompt_templates


def test_build_rag_prompt_includes_language():
    q = "What is malaria?"
    ctx = "Some context"
    prompt_en = prompt_templates.build_rag_prompt(q, ctx, detail_level="Standard", language="English")
    assert "Respond in English" in prompt_en or "Respond in English" in prompt_en

    prompt_pidgin = prompt_templates.build_rag_prompt(q, ctx, detail_level="Standard", language="Pidgin")
    assert "Respond in Pidgin" in prompt_pidgin
