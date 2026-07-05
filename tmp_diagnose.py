import os, json
print('GOOGLE_API_KEY present:', bool(os.getenv('GOOGLE_API_KEY')))
from backend.core.llm_engine import llm_engine
status = llm_engine.get_status()
print('LLM status:', json.dumps(status, indent=2))
try:
    out = llm_engine.generate('What is malaria?', max_tokens=64)
    print('\nSample generate output:\n', out)
except Exception as e:
    print('Generate error:', e)
