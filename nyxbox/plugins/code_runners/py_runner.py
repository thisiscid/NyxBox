import asyncio
import tempfile
import os
import sys
import re

TIMEOUT=3

async def run_python_code(code, challenge, is_submission=False, is_guest=False):
    all_results = []
    if is_guest:
        pattern = r'^\s*(?:import\s+\w+(?:\s+as\s+\w+)?|from\s+[A-Za-z0-9_\.]+\s+import\s+)'
        if re.search(pattern, code, re.MULTILINE):
            return [{
                "input": None,
                "output": None,
                "expected_output": None,
                "passed": False,
                "error": "Imports are not allowed!"
            }]
    # Create test program
    if is_guest:
        test_code = f"""
{code}

import sys
func_name = '{challenge['function_name']}'
tests = {challenge['tests']}
is_submission = {is_submission}

import builtins, sys

sys.path[:] = ['']
_orig_import = builtins.__import__
def __blocked_import__(name, globals=None, locals=None, fromlist=(), level=0):
    print("Test 0: FAIL - Importing is not allowed!")
    exit()
builtins.__import__ = __blocked_import__

for i, test_case in enumerate(tests):
    if not is_submission and test_case.get('hidden', False):
        continue
    
    try:
        result = {challenge['function_name']}(*test_case['input'])
        expected = test_case['expected_output']
        if result == expected:
            print(f"Test {{i+1}}: PASS")
        else:
            print(f"Test {{i+1}}: FAIL - Got: {{result}} Expected: {{expected}}")
    except Exception as e:
        print(f"Test {{i+1}}: ERROR - {{str(e)}}")
"""
    else:
        test_code = f"""
{code}

import sys
func_name = '{challenge['function_name']}'
tests = {challenge['tests']}
is_submission = {is_submission}

for i, test_case in enumerate(tests):
    if not is_submission and test_case.get('hidden', False):
        continue    
    try:
        result = {challenge['function_name']}(*test_case['input'])
        expected = test_case['expected_output']
        if result == expected:
            print(f"Test {{i+1}}: PASS")
        else:
            print(f"Test {{i+1}}: FAIL - Got: {{result}} Expected: {{expected}}")
    except Exception as e:
        print(f"Test {{i+1}}: ERROR - {{str(e)}}")
"""
    
    # Write to temp file and execute
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp_file:
        tmp_file.write(test_code)
        tmp_file_name = tmp_file.name
    
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-I", "-S", tmp_file_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=TIMEOUT)
        except asyncio.TimeoutError:
            try:
                process.kill()
                await process.wait()
            except:
                pass
            return [{"input": "Execution", "output": None, "expected_output": None, "passed": False, "error": f"Execution timed out, Timeout = {TIMEOUT}"}]
        
        if stderr:
            stderr_text = stderr.decode('utf-8', errors='replace').strip()
            return [{"input": None, "output": None, "expected_output": None, "passed": False, "error": stderr_text}]
        
        # Parse results
        output_lines = stdout.decode('utf-8', errors='replace').strip().split('\n')
        test_cases = [t for t in challenge['tests'] if is_submission or not t.get('hidden', False)]
        
        for i, line in enumerate(output_lines):
            if line.startswith("Test ") and i < len(test_cases):
                test_case = test_cases[i]
                
                if ": PASS" in line:
                    all_results.append({
                        "input": str(test_case["input"]),
                        "output": str(test_case["expected_output"]),
                        "expected_output": str(test_case["expected_output"]),
                        "passed": True,
                        "error": None
                    })
                elif ": FAIL" in line:
                    try:
                        fail_part = line.split(": FAIL - Got: ")[1]
                        actual_output, expected_output = fail_part.split(" Expected: ", 1)
                        all_results.append({
                            "input": str(test_case["input"]),
                            "output": actual_output,
                            "expected_output": expected_output,
                            "passed": False,
                            "error": None
                        })
                    except:
                        all_results.append({
                            "input": str(test_case["input"]),
                            "output": None,
                            "expected_output": str(test_case["expected_output"]),
                            "passed": False,
                            "error": "Failed to parse test output"
                        })
                elif ": ERROR" in line:
                    try:
                        error_message = line.split(": ERROR - ")[1]
                    except:
                        error_message = "Unknown error"
                    all_results.append({
                        "input": str(test_case["input"]),
                        "output": None,
                        "expected_output": str(test_case["expected_output"]),
                        "passed": False,
                        "error": error_message
                    })
                    if is_submission:
                        break
    
    finally:
        try:
            os.unlink(tmp_file_name)
        except:
            pass
    
    if is_submission:
        # Return only up to first failed test
        for i, result in enumerate(all_results):
            if not result["passed"]:
                return all_results[:i+1]
    
    return all_results