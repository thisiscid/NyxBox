import os
import json
import tempfile
import asyncio
import shutil
#This file is largely unused since C isn't supported and I can't bother for the life of me to do the custom dicts
# I don't evne know how to write C
async def run_c_code(user_code, func_name, test_cases, standard):
    """
    Run C++ code against test cases and return results.
    """    
    c_code = generate_c_program(user_code, func_name, test_cases)

    # TODO: Write the program to a temporary file, compile it, run it, and capture output
    results = await compile_and_run(c_code, test_cases, standard)
    # TODO: Return a list of dictionaries containing test results
    return results

def generate_c_program(user_code, func_name, test_cases):
    """
    Generate a C program with test code.
    """
    test_code = generate_test_code(func_name, test_cases)
    program_template = """
#include <stdio.h>
#include <stdbool.h>
#include <stddef.h>

// ===== USER CODE START =====
{user_code}
// ===== USER CODE END =====

int main(void) {{
    int all_passed = 1;

{test_code}

    printf("%s\\n", all_passed ? "ALL TESTS PASSED" : "SOME TESTS FAILED");
    return all_passed ? 0 : 1;
}}"""
    ret = program_template.format(user_code=user_code, test_code=test_code)
    return ret

def generate_test_code(func_name, test_cases):
    """
    Generate C++ code that tests the user's function.
    """
    test_code_blocks=[]
    # TODO: Create a list to hold test code blocks
    for i, test in enumerate(test_cases):
        if test.get("hidden", False):
            continue
        inputs = test.get('input', [])
        expected = test.get('expected_output')
        input_vars = []
        input_args = []
        for j, input_val in enumerate(inputs):
            c_type = infer_c_type(input_val)
            var_name = f"input_{i}_{j}"
            c_value = python_to_c_value(input_val)
            input_vars.append(f"    {c_type} {var_name} = {c_value};")
            input_args.append(var_name)

        expected_type = infer_c_type(expected)
        expected_var = f"expected_{i}"
        expected_value = python_to_c_value(expected)

    # TODO: For each test case:
    #   - Get input values and expected output
    #   - Create C++ variables for inputs with correct types
    #   - Create variable for expected output
    #   - Add code to call the function and compare results
    #   - Print PASS/FAIL with appropriate information
    
    # TODO: Join all test blocks into a single string and return it
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

def python_to_c_value(value):
    """
    Convert Python values to C++ literals.
    """
    if value is None:
        return "NULL"
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
        elements = [python_to_c_value(item) for item in value]
        return "{" + ", ".join(elements) + "}"
    elif isinstance(value, dict):
        pairs = ["{" + python_to_c_value(k) + ", " + python_to_c_value(v) + "}" 
                 for k, v in value.items()]
        return "{" + ", ".join(pairs) + "}"
    else:
        return "Warning: Unsupported type!"


def infer_c_type(value):
    """
    Determine the appropriate C++ type for a Python value.
    """
    if value is None:
        return "nullptr"
    elif isinstance(value, bool):
        return "bool"
    elif isinstance(value, int):
        return "int"
    elif isinstance(value, float):
        return "double"
    elif isinstance(value, str):
        return "string"
    elif isinstance(value, list):
        if not value:
            return "vector<int>"
        first_type = type(value[0])
        if all(isinstance(item, first_type) for item in value):
            element_type = infer_c_type(value[0])
            return f"vector<{element_type}>"
        else:
            return "vector<auto>"  # Not valid C++ but indicates a type issue
    elif isinstance(value, dict):
        if not value:
            return "map<string, int>"  # Default for empty dict
        
        key, val = next(iter(value.items()))
        key_type = infer_c_type(key)
        val_type = infer_c_type(val)
        return f"map<{key_type}, {val_type}>"
    else:
        return "auto"
    # TODO: Determine C++ type based on Python type:
    #   - None → nullptr_t
    #   - bool → bool
    #   - int → int
    #   - float → double
    #   - str → string
    #   - list → vector<appropriate_type>
    #   - dict → map<key_type, value_type>

async def compile_and_run(c_code, test_cases, standard):
    """
    Compile and run C++ code, then parse the results.
    """
    tmp_c_file = None
    executable = None
    results = []
    
    try:
        # TODO: Create a temporary file for the C++ code
        with tempfile.NamedTemporaryFile(suffix='.cpp', delete=False) as tmp_file:
            tmp_c_file = tmp_file.name
            tmp_file.write(c_code.encode('utf-8'))
        # TODO: Find a C++ compiler (g++ or clang++)
        executable = tmp_c_file + ('.exe' if os.name == 'nt' else '')
        compiler = shutil.which("gcc") or shutil.which("clang")
        if not compiler:
            return [{
                    "input": "Compiler check",
                    "output": None,
                    "expected_output": None,
                    "passed": False,
                    "error": "No compiler found."
                }]
        compiler_process = await asyncio.create_subprocess_exec(
            compiler, f'-std={standard}', tmp_c_file, '-o', executable, 
            stdout = asyncio.subprocess.PIPE, stderr = asyncio.subprocess.PIPE
        )
        try:
            _, stderr = await asyncio.wait_for(compiler_process.communicate(), timeout=20.0)
            # TODO: Compile the code with appropriate flags
            if compiler_process.returncode != 0:
                # Compiler reached error, return the error
                # TODO: Handle compilation errors Done
                return [{
                        "input": f"{compiler} -std={standard} {tmp_c_file} -o {executable}",
                        "output": None,
                        "expected_output": None,
                        "passed": False,
                        "error": stderr.decode('utf-8', errors='replace').strip()
                    }]
        except asyncio.TimeoutError:
            return [{
            "input": f"{compiler} -std={standard} {tmp_c_file} -o {executable}",
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
            if tmp_c_file is not None and os.path.exists(tmp_c_file):
                os.unlink(tmp_c_file)
            if executable is not None and os.path.exists(executable):
                os.unlink(executable)
        except Exception as e:
            print(f"Error cleaning up temp files: {e}")
    return results