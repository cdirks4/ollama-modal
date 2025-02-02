import modal
import os
import subprocess
import time

from modal import build, enter, method

MODEL = "deepseek-r1:671b"  # Using the correct model name format

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

@app.cls(gpu="H100", container_idle_timeout=300)
class Ollama:
    @enter()
    def load(self):
        # Pull model on every container start
        subprocess.run(["systemctl", "start", "ollama"])
        time.sleep(5)  # Wait for ollama to start
        pull(MODEL)  # Pull model before any inference

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
    for chunk in ollama.infer.remote_gen(text):
        print(chunk, end='', flush=False)