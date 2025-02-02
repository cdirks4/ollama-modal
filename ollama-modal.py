import modal
import os
import subprocess
import time
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from modal import build, enter, method

MODEL = "deepseek-r1:32b"  # Using the correct model name format

def pull(model: str = MODEL):
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "enable", "ollama"])
    subprocess.run(["systemctl", "start", "ollama"])
    time.sleep(10)  # Ensure service is fully started
    print(f"Pulling model {model}...")
    result = subprocess.run(["ollama", "pull", model], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1200)
    if result.returncode != 0:
        print(f"Error pulling model: {result.stderr.decode()}")
        raise Exception(f"Failed to pull model {model}")
    print("Model pulled successfully")

image = (
    modal.Image
    .debian_slim()
    .apt_install("curl", "systemctl")
    .run_commands(
        "curl -L https://ollama.com/download/ollama-linux-amd64.tgz -o ollama-linux-amd64.tgz",
        "tar -C /usr -xzf ollama-linux-amd64.tgz",
        "useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama",
        "usermod -a -G ollama $(whoami)",
    )
    .copy_local_file("ollama.service", "/etc/systemd/system/ollama.service")
    .pip_install("ollama")
)

app = modal.App(name="ollama", image=image)

with image.imports():
    import ollama

web_app = FastAPI()
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@web_app.get("/")
async def root():
    return {"status": "ok", "model": MODEL}

@web_app.post("/generate")
async def generate(text: str):
    ollama = Ollama()
    responses = []
    async def process_parallel():
        tasks = []
        for _ in range(8):
            tasks.append(ollama.infer.remote_gen(text))
        return await asyncio.gather(*tasks)
    
    responses = await process_parallel()
    return {"responses": [list(r) for r in responses]}

# Mount the FastAPI app
stub = modal.Stub(name="ollama-api", image=image)

@stub.function(gpu="H100",
    container_idle_timeout=None,
    concurrency_limit=8)
@modal.asgi_app()
def api():
    return web_app

@app.cls(
    gpu="H100",
    container_idle_timeout=None,  # No timeout
    concurrency_limit=8,  # Use exactly 8 H100s
)
class Ollama:
    @enter()
    def load(self):
        subprocess.run(["systemctl", "start", "ollama"])
        time.sleep(5)
        pull(MODEL)

    @method()
    def infer(self, text: str):
        stream = ollama.chat(
            model=MODEL,
            messages=[{'role': 'user', 'content': text}],
            stream=True
        )
        for chunk in stream:
            yield chunk['message']['content']
            print(chunk['message']['content'], end='', flush=True)
        return

# Convenience thing, to run using:
#
#  $ modal run ollama-modal.py [--lookup] [--text "Why is the sky blue?"]
@app.local_entrypoint()
def main(text: str = "Why is the sky blue?", lookup: bool = False):
    if lookup:
        ollama = modal.Cls.lookup("ollama", "Ollama")
    else:
        ollama = Ollama()
    
    # Create 8 parallel instances all working on the same text
    async def process_parallel():
        tasks = []
        for _ in range(8):  # Always use 8 instances
            tasks.append(ollama.infer.remote_gen(text))
        return await asyncio.gather(*tasks)
    
    # Run all 8 instances and collect responses
    responses = asyncio.run(process_parallel())
    
    # Print responses from all 8 instances
    for i, response in enumerate(responses):
        print(f"\nH100 GPU {i + 1} Response:")
        for chunk in response:
            print(chunk, end='', flush=True)
        print("\n" + "-"*50)  # Separator between responses