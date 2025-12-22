import os
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

import subprocess
import json
from pathlib import Path
from datetime import datetime, timezone

from prompts import PROMPTS
from config import TEMPERATURES, CONTEXT_LENGTHS, TEST_INPUT

def build_model(model_name: str, modelfile_path: Path):
    subprocess.run(
        ["ollama", "create", model_name, "-f", str(modelfile_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )


def run_ollama(model_name: str, prompt: str) -> str:
    proc = subprocess.Popen(
        ["ollama", "run", model_name],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    stdout, _ = proc.communicate(prompt.encode("utf-8"))
    return stdout.decode("utf-8", errors="replace").strip()

def create_modelfile(model_name, system_prompt, temperature):
    path = Path("modelfiles") / f"{model_name}.modelfile"
    path.parent.mkdir(exist_ok=True)

    path.write_text(
        f"""
FROM tinyllama
SYSTEM {system_prompt}
PARAMETER temperature {temperature}
""".strip(),
        encoding="utf-8"
    )
    return path

def main():
    results = []
    results_dir = Path("results")
    outputs_dir = results_dir / "outputs"

    outputs_dir.mkdir(parents=True, exist_ok=True)

    for prompt_name, system_prompt in PROMPTS.items():
        for temp in TEMPERATURES:
            model_name = f"tinyllama_{prompt_name}_t{temp}".replace(".", "_")

            modelfile = create_modelfile(model_name, system_prompt, temp)
            build_model(model_name, modelfile)

            for ctx_len in CONTEXT_LENGTHS:
                truncated_input = TEST_INPUT[:ctx_len]

                full_prompt = f"""
{system_prompt}

INPUT:
{truncated_input}

TASK:
Write a cognitive and attention-related summary.
"""

                output = run_ollama(model_name, full_prompt)

                record = {
                    "model": model_name,
                    "prompt_variant": prompt_name,
                    "temperature": temp,
                    "context_length": ctx_len,
                    "output": output,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                results.append(record)

                out_file = outputs_dir / f"{model_name}_ctx{ctx_len}.txt"
                out_file.write_text(output, encoding="utf-8")

    with open(results_dir / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Completed {len(results)} runs.")

if __name__ == "__main__":
    main()
