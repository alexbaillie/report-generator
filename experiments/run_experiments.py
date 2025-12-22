import os
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

import subprocess
import json
from pathlib import Path
from datetime import datetime, timezone

from prompts import PROMPTS
from config import TEMPERATURES, CONTEXT_LENGTHS, TEST_INPUT

# Template content for report generation
TEMPLATE_CONTENT = """
Generate a professional neuropsychological report following this exact structure:

Psych Report Template

PATIENT
Name:
Chart number:
Date of birth:
Date of assessment:
Age at assessment:	
Date of conference:	
Legal guardian:	
		
TEAM
Developmental Pediatrician:	
Psychologist:	
Assessing Clinician:	
Speech Language Pathologist:	
Social worker:	
Case manager:   

CONTENTS

SUMMARIES
Diagnostic summary:
Summary of findings:

RECOMMENDATIONS FOR SERVICE

STRATEGIES
Allowances:
Accommodations:
Instructional Strategies:

SUPPORTING INFORMATION
Reason for referral:
Sources of information:
Background information:
- Presenting concerns (as provided by...)
- Family History
- Developmental and Medical History
- Educational History
- Previous Schools and Programming
- Previous Assessments & Interventions
Behavioural Observations:
Tests administered:
Parent/teacher report measures administered:
Information on the interpretation of test scores:

APPENDICES 

Please fill in each section with appropriate content based on the provided documents and additional information. Use professional psychological terminology and ensure the report is comprehensive and clinically accurate.
"""

# Simulated additional inputs
ADDITIONAL_INPUTS = {
    "session_observations": """
During the assessment session, the child appeared cooperative and engaged. She demonstrated good rapport with the examiner and appeared motivated to perform well on tasks. Attention was variable throughout the session, with occasional distractibility noted. The child required frequent redirection to maintain focus on test items. No significant behavioral concerns were observed during testing.
""",
    "previous_reports": """
Previous psychological evaluation completed 2 years ago indicated similar concerns with attention and executive functioning. At that time, the child was diagnosed with ADHD and started on stimulant medication. Parent reports mixed response to medication, with some improvement in focus but continued challenges with organization and task completion.
""",
    "other_info": """
The child attends a specialized program for students with learning differences. She receives additional support in reading and math. Parent reports that homework takes significantly longer than expected, often requiring 2-3 hours per night. The child enjoys art and music activities and participates in soccer after school.
"""
}

def build_experiment_prompt(system_prompt: str, context_length: int) -> str:
    """Build a prompt similar to the actual report generation process"""
    truncated_input = TEST_INPUT[:context_length]
    
    prompt_parts = [
        "You are a professional psychologist writing a psychological report.",
        f"\nReport Type: evaluation",
        f"\nTemplate Instructions:\n{TEMPLATE_CONTENT}",
    ]
    
    # Add document content
    prompt_parts.append("\n\nSource Documents:")
    prompt_parts.append(f"\n--- Test Data ---")
    prompt_parts.append(truncated_input)
    
    # Add additional inputs
    if ADDITIONAL_INPUTS:
        prompt_parts.append("\n\nAdditional Information:")
        for key, value in ADDITIONAL_INPUTS.items():
            prompt_parts.append(f"\n{key}: {value}")
    
    prompt_parts.append("\n\nPlease generate a professional psychological report based on the above information. The report should be well-structured, clear, and follow professional standards.")
    
    return "\n".join(prompt_parts)

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
                full_prompt = build_experiment_prompt(system_prompt, ctx_len)

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
