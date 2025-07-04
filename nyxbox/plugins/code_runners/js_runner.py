import json
import tempfile
import asyncio
import subprocess
import re
async def run_js_code(code, challenge, is_submission = False, is_guest = False) -> list:
    all_results=[]
    if is_guest:
        if re.search(r'\b(import\s+|require\s*\()', code):
            return [{
                "input": None,
                "output": None,
                "expected_output": None,
                "passed": False,
                "error": "Use of import/require is disallowed"
            }]
    for test_case in challenge['tests']:
        if test_case.get("hidden", False) and not is_submission:
            continue
        args = ", ".join(json.dumps(arg) for arg in test_case["input"])
        expected = test_case["expected_output"]
        wrapped_code = f"""
// --- USER CODE START ---
{code}
// --- USER CODE END ---

try {{
const result = {challenge.get('function_name')}({args});
console.log(JSON.stringify(result));
}} catch (err) {{
console.error("ERROR:", err.message);
process.exit(1);
}}
"""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".js") as f:
            f.write(wrapped_code)
            js_file = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
            "node", js_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=3)
            if proc.returncode != 0:
                all_results.append({
                    "input": str(test_case["input"]),
                    "output": None,
                    "expected_output": json.dumps(expected),
                    "passed": False,
                    "error": stderr.decode().strip()
                })
                continue
            else:
                result = json.loads(stdout.decode().strip())
                # Compare None/null correctly
                if expected is None:
                    passed = result is None
                else:
                    passed = result == expected
                all_results.append({
                    "input": str(test_case["input"]),
                    "output": json.dumps(result),
                    "expected_output": json.dumps(expected),
                    "passed": passed,
                    "error": None
                })
        except asyncio.TimeoutError:
            all_results.append({
                "input": str(test_case["input"]),
                "output": None,
                "expected_output": json.dumps(expected),
                "passed": False,
                "error": "Execution timed out"
            })
    return all_results