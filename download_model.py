import os
import requests
import time

url = "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
dest = r"c:\Users\HP\Desktop\AfriHealth-Assistant\backend\models\llm\llama-3-8b-q4.gguf"

def download_with_resume(url, dest, max_retries=15):
    headers = {}
    if os.path.exists(dest):
        downloaded = os.path.getsize(dest)
        headers["Range"] = f"bytes={downloaded}-"
    else:
        downloaded = 0
    
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt+1}: downloading from byte {downloaded}...")
            with requests.get(url, headers=headers, stream=True, timeout=15) as r:
                if r.status_code == 416:
                    print("Download complete (416).")
                    return True
                r.raise_for_status()
                with open(dest, "ab" if downloaded > 0 else "wb") as f:
                    for chunk in r.iter_content(chunk_size=81920):
                        if chunk:
                            f.write(chunk)
            print("Download successful!")
            return True
        except Exception as e:
            print(f"Error on attempt {attempt+1}: {e}")
            time.sleep(3)
            if os.path.exists(dest):
                downloaded = os.path.getsize(dest)
                headers["Range"] = f"bytes={downloaded}-"
    return False

if __name__ == "__main__":
    download_with_resume(url, dest)
