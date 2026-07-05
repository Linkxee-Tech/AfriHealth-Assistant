from pathlib import Path
import traceback
p = Path('backend/models/llm/llama-3-8b-q4.gguf')
print('exists', p.exists())
print('resolve', p.resolve())
print('size', p.stat().st_size if p.exists() else 'n/a')
print('is_file', p.is_file())
from llama_cpp import Llama
try:
    Llama(model_path=str(p), n_threads=1, n_ctx=512)
    print('model loaded OK')
except Exception as e:
    print('load failed:', repr(e))
    traceback.print_exc()
