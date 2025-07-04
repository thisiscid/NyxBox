import os
import json
import tempfile
import asyncio
import re

ALLOWED_JAVA_IMPORT_PREFIXES = [
    "java.util.",   
    "java.math.",    
]

async def run_java_code(user_code, func_name, test_cases, jdk_path, is_submission=False, is_guest=False):
    """
    Run java code against test cases and return results.
    """   
    if is_guest:
        imports = re.findall(r'^\s*import\s+([\w\.]+\*?);\s*$', user_code, re.MULTILINE)
        for imp in imports:
            if not any(imp.startswith(prefix) for prefix in ALLOWED_JAVA_IMPORT_PREFIXES):
                return [{
                "input": None,
                "output": None,
                "expected_output": None,
                "passed": False,
                "error": "Use of import statements is disallowed"
                }]
    if is_submission:
        filtered_tests = test_cases  # All tests, including hidden
    else:
        filtered_tests = [t for t in test_cases if not t.get("hidden", False)]
    java_code = generate_java_program(user_code, func_name, filtered_tests, is_submission)

    results = await compile_and_run(java_code, filtered_tests, jdk_path, is_submission)
    return results

def generate_java_program(user_code, func_name, test_cases, is_submission=False):
    """
    Generate a java program with test code.
    """
    test_code = generate_test_code(func_name, test_cases, is_submission)
    program_template = """
import java.util.Map;
import java.util.HashMap;
import java.util.Arrays;

public class Solution {{
    // ===== USER CODE START =====
{user_code}
    // ===== USER CODE END =====

    public static void main(String[] args) {{
        boolean all_passed = true;
{test_code}
        System.out.println(all_passed ? "ALL TESTS PASSED" : "SOME TESTS FAILED");
    }}
}}
"""
    return program_template.format(user_code=user_code, test_code=test_code)

def generate_comparison_code(expected_type, result_var, expected_var):
    """
    Generate appropriate comparison code based on the type.
    """
    if expected_type.endswith("[]"):
        return f"Arrays.equals({result_var}, {expected_var})"
    else:
        return f"{result_var}.equals({expected_var})" if expected_type in ["String"] else f"{result_var} == {expected_var}"

def generate_test_code(func_name, test_cases, is_submission=False):
    """
    Generate java code that tests the user's function.
    """
    test_code_blocks=[]
    if is_submission:
        for i, test in enumerate(test_cases):
            inputs = test.get('input', [])
            expected = test.get('expected_output')
            input_vars = []
            input_args = []
            for j, input_val in enumerate(inputs):
                java_type = infer_java_type(input_val)
                var_name = f"input_{i}_{j}"
                java_value = python_to_java_value(input_val)
                input_vars.append(f"    {java_type} {var_name} = {java_value};")
                input_args.append(var_name)

            expected_type = infer_java_type(expected)
            expected_var = f"expected_{i}"
            expected_value = python_to_java_value(expected)
            
            test_block = f"""
        // Test case {i+1}
        System.out.print("Test {i+1}: ");
        try {{
{chr(10).join(input_vars)}
            {expected_type} {expected_var} = {expected_value};

            // Call the function with test inputs
            {expected_type} result = {func_name}({", ".join(input_args)});

            // Compare result with expected output
            if ({generate_comparison_code(expected_type, "result", expected_var)}) {{
                System.out.println("PASS");
            }} else {{
                all_passed = false;
                System.out.println("FAIL - Got: " + {get_display_string(expected_type, "result")} + ", Expected: " + {get_display_string(expected_type, expected_var)});
            }}
        }} catch (Exception e) {{
            all_passed = false;
            System.out.println("ERROR - " + e.getMessage());
        }}
"""
            test_code_blocks.append(test_block)
    else:
        for i, test in enumerate(test_cases):
            if test.get("hidden", False):
                continue
            inputs = test.get('input', [])
            expected = test.get('expected_output')
            input_vars = []
            input_args = []
            for j, input_val in enumerate(inputs):
                java_type = infer_java_type(input_val)
                var_name = f"input_{i}_{j}"
                java_value = python_to_java_value(input_val)
                input_vars.append(f"    {java_type} {var_name} = {java_value};")
                input_args.append(var_name)

            expected_type = infer_java_type(expected)
            expected_var = f"expected_{i}"
            expected_value = python_to_java_value(expected)

            test_block = f"""
        // Test case {i+1}
        System.out.print("Test {i+1}: ");
        try {{
{chr(10).join(input_vars)}
            {expected_type} {expected_var} = {expected_value};

            // Call the function with test inputs
            {expected_type} result = {func_name}({", ".join(input_args)});

            // Compare result with expected output
            if ({generate_comparison_code(expected_type, "result", expected_var)}) {{
                System.out.println("PASS");
            }} else {{
                all_passed = false;
                System.out.println("FAIL - Got: " + {get_display_string(expected_type, "result")} + ", Expected: " + {get_display_string(expected_type, expected_var)});
            }}
        }} catch (Exception e) {{
            all_passed = false;
            System.out.println("ERROR - " + e.getMessage());
        }}
"""
            test_code_blocks.append(test_block)

    return "\n".join(test_code_blocks)

def python_to_java_value(value, var_name="map"):
    """
    Convert Python values to java literals.
    """
    if value is None:
        return "null"
    elif isinstance(value, bool):
        if value:
            return "true"
        return "false"
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, float):
        return str(value)
    elif isinstance(value, str):
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    elif isinstance(value, list):
        elements = [python_to_java_value(item) for item in value]
        return "{" + ", ".join(elements) + "}"
    elif isinstance(value, dict):
        key_type = infer_java_type(next(iter(value.keys())))
        val_type = infer_java_type(next(iter(value.values())))
        lines = [f"Map<{key_type}, {val_type}> {var_name} = new HashMap<>();"]
        for k, v in value.items():
            lines.append(f'{var_name}.put({python_to_java_value(k)}, {python_to_java_value(v)});')
        return "\n".join(lines)
    else:
        return "null"


def infer_java_type(value):
    """
    Determine the appropriate java type for a Python value.
    """
    if value is None:
        return "Object"
    elif isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "int"
    elif isinstance(value, float):
        return "double"
    elif isinstance(value, str):
        return "String"
    elif isinstance(value, list):
        if not value:
            return "int[]"
        first_type = type(value[0])
        if all(isinstance(item, first_type) for item in value):
            element_type = infer_java_type(value[0])
            return f"{element_type}[]"
        else:
            return "int[]"
    elif isinstance(value, dict):
        if not value:
            return "Map<String, Integer>"  # Default for empty dicts
        key, val = next(iter(value.items()))
        key_type = infer_java_type(key)
        val_type = infer_java_type(val)
        return f"Map<{key_type}, {val_type}>"
    else:
        return "Object"

async def compile_and_run(java_code, test_cases, jdk_path, is_submission):
    """
    Compile and run java code, then parse the results.
    """
    tmp_java_file = None
    results = []
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_java_file = os.path.join(tmpdir, "Solution.java")
            with open(tmp_java_file, "w") as tmp_file:
                tmp_file.write(java_code)
            compiler_process = await asyncio.create_subprocess_exec(
                os.path.join(jdk_path, "bin", "javac"), tmp_java_file,
                stdout = asyncio.subprocess.PIPE, stderr = asyncio.subprocess.PIPE
            )
            try:
                _, stderr = await asyncio.wait_for(compiler_process.communicate(), timeout=20.0)
                if compiler_process.returncode != 0:
                    return [{
                            "input": f"{os.path.join(jdk_path, 'bin', 'javac')} {tmp_java_file}",
                            "output": None,
                            "expected_output": None,
                            "passed": False,
                            "error": stderr.decode('utf-8', errors='replace').strip()
                        }]
            except asyncio.TimeoutError:
                return [{
                "input": f"{jdk_path} {tmp_java_file} ",
                "output": None,
                "expected_output": None,
                "passed": False,
                "error": "Execution timed out (20 seconds)"
            }]

            process = await asyncio.create_subprocess_exec(
                os.path.join(jdk_path, "bin", "java"), "-cp", tmpdir, "Solution",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=20.0)
            except asyncio.TimeoutError:
                return [{
                "input": "Execution",
                "output": None,
                "expected_output": None,
                "passed": False,
                "error": "Execution timed out (20 seconds)"
            }]

            for test in stdout.decode('utf-8', errors='replace').splitlines():
                if "Test " in test:
                    new1_test=test.split("Test ")
                    test_index=int(new1_test[1].split(":")[0])-1
                    if "PASS" in test:
                        results.append({"input": test_cases[test_index]["input"], 
                                        "output": python_to_java_value(test_cases[test_index]['expected_output']), 
                                        "expected_output": python_to_java_value(test_cases[test_index]['expected_output']),
                                        "passed": True,
                                        "error": None})
                    elif "FAIL" in test:
                        fail_str = new1_test[1].split("FAIL - Got: ")[1]
                        actual_output, expected_output = fail_str.split(", Expected: ")
                        results.append({"input": test_cases[test_index]["input"], 
                                        "output": actual_output, 
                                        "expected_output": expected_output, 
                                        "passed": False,
                                        "error": None})
    finally:
        try:
            if tmp_java_file is not None and os.path.exists(tmp_java_file):
                os.unlink(tmp_java_file)
        except Exception as e:
            print(f"Error cleaning up temp files: {e}")
    return results

def get_display_string(java_type, var_name):
    """Generate appropriate string representation for display."""
    if java_type.endswith("[]"):
        return f"Arrays.toString({var_name})"
    else:
        return var_name