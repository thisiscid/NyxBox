import os
import json
import tempfile
import asyncio
import shutil

async def run_java_code(user_code, func_name, test_cases, standard, is_submission=False):
    """
    Run C++ code against test cases and return results.
    """    
    # TODO: Generate a complete C++ program that includes the user's code and test functions
    if is_submission:
        filtered_tests = test_cases  # All tests, including hidden
    else:
        filtered_tests = [t for t in test_cases if not t.get("hidden", False)]
    java_code = generate_java_program(user_code, func_name, filtered_tests, is_submission)

    # TODO: Write the program to a temporary file, compile it, run it, and capture output
    results = await compile_and_run(java_code, filtered_tests, standard, is_submission)
    # TODO: Return a list of dictionaries containing test results
    return results

def generate_java_program(user_code, func_name, test_cases, is_submission=False):
    """
    Generate a C++ program with test code.
    """
    test_code = generate_test_code(func_name, test_cases, is_submission)
    program_template = """
import java.util.Map;
import java.util.HashMap;

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
def generate_test_code(func_name, test_cases, is_submission=False):
    """
    Generate C++ code that tests the user's function.
    """
    test_code_blocks=[]
    # TODO: Create a list to hold test code blocks
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
    cout << "Test {i+1}: ";
    try {{
{chr(10).join(input_vars)}
        {expected_type} {expected_var} = {expected_value};

        // Call the function with test inputs
        auto result = {func_name}({", ".join(input_args)});

        // Compare result with expected output
        if (result == {expected_var}) {{
            cout << "PASS" << endl;
        }} else {{
            all_passed = false;
            cout << "FAIL - Got: " << result << ", Expected: " << {expected_var} << endl;
        }}
    }} catch (exception& e) {{
        all_passed = false;
        cout << "ERROR - " << e.what() << endl;
    }}"""
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
    cout << "Test {i+1}: ";
    try {{
{chr(10).join(input_vars)}
        {expected_type} {expected_var} = {expected_value};

        // Call the function with test inputs
        auto result = {func_name}({", ".join(input_args)});

        // Compare result with expected output
        if (result == {expected_var}) {{
            cout << "PASS" << endl;
        }} else {{
            all_passed = false;
            cout << "FAIL - Got: " << result << ", Expected: " << {expected_var} << endl;
        }}
    }} catch (exception& e) {{
        all_passed = false;
        cout << "ERROR - " << e.what() << endl;
    }}"""
            test_code_blocks.append(test_block)

    return "\n".join(test_code_blocks)

def python_to_java_value(value, var_name="map"):
    """
    Convert Python values to C++ literals.
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
    Determine the appropriate C++ type for a Python value.
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
    # TODO: Determine C++ type based on Python type:
    #   - None → nullptr_t
    #   - bool → bool
    #   - int → int
    #   - float → double
    #   - str → string
    #   - list → vector<appropriate_type>
    #   - dict → map<key_type, value_type>

async def compile_and_run(java_code, test_cases, standard, is_submission):
    """
    Compile and run C++ code, then parse the results.
    """
    tmp_java_file = None
    executable = None
    results = []
    
    try:
        # TODO: Create a temporary file for the C++ code
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_java_file = os.path.join(tmpdir, "Solution.java")
            with open(tmp_java_file, "w") as tmp_file:
                tmp_file.write(java_code)
        # TODO: Find a C++ compiler (g++ or clang++)
        executable = tmp_java_file + ('.exe' if os.name == 'nt' else '')
        compiler = shutil.which("javac")
        if not compiler:
            return [{
                    "input": "Compiler check",
                    "output": None,
                    "expected_output": None,
                    "passed": False,
                    "error": "No compiler found."
                }]
        compiler_process = await asyncio.create_subprocess_exec(
            compiler, tmp_java_file,
            stdout = asyncio.subprocess.PIPE, stderr = asyncio.subprocess.PIPE
        )
        try:
            _, stderr = await asyncio.wait_for(compiler_process.communicate(), timeout=20.0)
            # TODO: Compile the code with appropriate flags
            if compiler_process.returncode != 0:
                # Compiler reached error, return the error
                # TODO: Handle compilation errors Done
                return [{
                        "input": f"{compiler} -std={standard} {tmp_java_file} -o {executable}",
                        "output": None,
                        "expected_output": None,
                        "passed": False,
                        "error": stderr.decode('utf-8', errors='replace').strip()
                    }]
        except asyncio.TimeoutError:
            return [{
            "input": f"{compiler} -std={standard} {tmp_java_file} -o {executable}",
            "output": None,
            "expected_output": None,
            "passed": False,
            "error": "Execution timed out (20 seconds)"
        }]

        # TODO: Run the compiled program with a timeout
        if os.name == 'nt':
            process = await asyncio.create_subprocess_exec(
            executable,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        else:
            process = await asyncio.create_subprocess_exec(
            executable, 
            stdout = asyncio.subprocess.PIPE, 
            stderr = asyncio.subprocess.PIPE
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

        # TODO: Parse the output to determine which tests passed or failed
        for test in stdout.decode('utf-8', errors='replace').splitlines():
            if "Test " in test:
                new1_test=test.split("Test ") # ["1: PASS"]
                # ["Test ", "1: FAIL - Got: x Expected: y"]
                test_index=int(new1_test[1].split(":")[0])-1
                if "PASS" in test:
                    results.append({"input": test_cases[test_index]["input"], 
                                    "output": test_cases[test_index]['expected_output'], 
                                    "expected_output": test_cases[test_index]['expected_output'],
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

        # TODO: Format results as a list of dictionaries
        
        # TODO: Clean up temporary files
    finally:
        try:
            if tmp_java_file is not None and os.path.exists(tmp_java_file):
                os.unlink(tmp_java_file)
            if executable is not None and os.path.exists(executable):
                os.unlink(executable)
        except Exception as e:
            print(f"Error cleaning up temp files: {e}")
    return results