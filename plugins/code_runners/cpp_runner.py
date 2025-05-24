# Yes, C++ was so complex I needed a seperate file to put it all in. Java will probably be the same.
# import os
# import json
# import tempfile
# import asyncio
# import shutil
# All of this is AI run code that I plan to use to understand + write my own
# This is your main function that will run C++ code
# async def run_cpp_code(user_code, func_name, test_cases):
#     """
#     Run C++ code against test cases and return results.
    
#     Parameters:
#     - user_code: The C++ code submitted by the user
#     - func_name: The name of the function to test
#     - test_cases: List of test cases with 'input' and 'expected_output'
    
#     Returns:
#     - List of dictionaries with test results (similar format to Python/JS runners)
#     """
#     # Step 1: Generate the C++ program
#     complete_code = generate_cpp_program(user_code, func_name, test_cases)
    
#     # Step 2-6: Write to file, compile, run, and parse results
#     return await compile_and_run(complete_code, test_cases)


# def generate_cpp_program(user_code, func_name, test_cases):
#     """
#     Generate a C++ program that includes the user's code and test cases.
#     """
#     # Get the test code blocks
#     test_code = generate_test_code(func_name, test_cases)
    
#     # Create a program template with only the extra includes needed for testing
#     program_template = """
# #include <stdexcept>  // Only adding what might be needed beyond user code

# // ===== USER CODE START =====
# {user_code}
# // ===== USER CODE END =====

# int main() {{
#     // Track if all tests passed
#     bool all_passed = true;
    
#     // Run each test case
# {test_code}
    
#     // Final result
#     cout << (all_passed ? "ALL TESTS PASSED" : "SOME TESTS FAILED") << endl;
    
#     // Return success/failure
#     return all_passed ? 0 : 1;
# }}
# """
    
#     # Fill in the template with user code and test code
#     complete_program = program_template.format(
#         user_code=user_code,
#         test_code=test_code
#     )
    
#     return complete_program


# def generate_test_code(func_name, test_cases):
#     """
#     Generate C++ code that tests the user's function against each test case.
#     """
#     test_code_blocks = []
    
#     for i, test in enumerate(test_cases):
#         if test.get("hidden", False):
#             continue  # Skip hidden tests
            
#         inputs = test.get("input", [])
#         expected = test.get("expected_output")
        
#         # 1. First, declare variables for inputs
#         input_vars = []
#         input_args = []
        
#         for j, input_val in enumerate(inputs):
#             cpp_type = infer_cpp_type(input_val)
#             var_name = f"input_{i}_{j}"
#             cpp_value = python_to_cpp_value(input_val)
            
#             # Declare the input variable with correct type and value
#             input_vars.append(f"    {cpp_type} {var_name} = {cpp_value};")
#             input_args.append(var_name)  # Remember variable name for function call
        
#         # 2. Declare expected output variable
#         expected_type = infer_cpp_type(expected)
#         expected_var = f"expected_{i}"
#         expected_value = python_to_cpp_value(expected)
        
#         # 3. Create code block for this test case
#         test_block = f"""
#     // Test case {i+1}
#     cout << "Test {i+1}: ";
#     try {{
# {chr(10).join(input_vars)}
#         {expected_type} {expected_var} = {expected_value};
        
#         // Call the function with test inputs
#         auto result = {func_name}({", ".join(input_args)});
        
#         // Compare result with expected output
#         if (result == {expected_var}) {{
#             cout << "PASS" << endl;
#         }} else {{
#             all_passed = false;
#             cout << "FAIL - Got: " << result << ", Expected: " << {expected_var} << endl;
#         }}
#     }} catch (exception& e) {{
#         all_passed = false;
#         cout << "ERROR - " << e.what() << endl;
#     }}"""
        
#         test_code_blocks.append(test_block)
    
#     # Combine all test blocks into a single string
#     return "\n".join(test_code_blocks)


# def python_to_cpp_value(value):
#     """
#     Convert a Python value to a C++ literal string.
    
#     Examples:
#     - True -> "true"
#     - 42 -> "42"
#     - "hello" -> "\"hello\""
#     - [1, 2, 3] -> "{1, 2, 3}"
#     """
#     if value is None:
#         return "nullptr"
#     elif isinstance(value, bool):
#         return "true" if value else "false"
#     elif isinstance(value, int):
#         return str(value)
#     elif isinstance(value, float):
#         return str(value)
#     elif isinstance(value, str):
#         # Escape quotes and create C++ string literal
#         escaped = value.replace('\\', '\\\\').replace('"', '\\"')
#         return f'"{escaped}"'
#     elif isinstance(value, list):
#         # For lists, create C++ initializer list
#         elements = [python_to_cpp_value(item) for item in value]
#         return "{" + ", ".join(elements) + "}"
#     elif isinstance(value, dict):
#         # For dictionaries, create C++ map initializer
#         pairs = ["{" + python_to_cpp_value(k) + ", " + python_to_cpp_value(v) + "}" 
#                 for k, v in value.items()]
#         return "{" + ", ".join(pairs) + "}"
#     else:
#         # Fallback for unsupported types
#         return str(value)


# def infer_cpp_type(value):
#     """
#     Infer the C++ type for a Python value.
    
#     Examples:
#     - bool -> "bool"
#     - int -> "int"
#     - str -> "string"
#     - [1, 2, 3] -> "vector<int>"
#     """
#     if value is None:
#         return "nullptr_t"
#     elif isinstance(value, bool):
#         return "bool"
#     elif isinstance(value, int):
#         return "int"
#     elif isinstance(value, float):
#         return "double"
#     elif isinstance(value, str):
#         return "string"
#     elif isinstance(value, list):
#         if not value:
#             return "vector<int>"  # Default for empty lists
        
#         # Check if all elements are the same type
#         element_type = type(value[0])
#         if all(isinstance(item, element_type) for item in value):
#             # Get C++ type for the element type
#             cpp_element_type = infer_cpp_type(value[0])
#             return f"vector<{cpp_element_type}>"
#         else:
#             # Mixed types, use auto or a more generic approach
#             return "vector<auto>"  # Not valid C++ but indicates a type issue
#     elif isinstance(value, dict):
#         if not value:
#             return "map<string, int>"  # Default for empty dict
        
#         # Get key and value types from first item
#         k, v = next(iter(value.items()))
#         key_type = infer_cpp_type(k)
#         val_type = infer_cpp_type(v)
#         return f"map<{key_type}, {val_type}>"
#     else:
#         # Fallback for unsupported types
#         return "auto"


# async def compile_and_run(cpp_code, test_cases):
#     """
#     Compile and run C++ code, then parse the results.
#     """
#     results = []
    
#     # 1. Write the code to a temp file
#     with tempfile.NamedTemporaryFile(suffix='.cpp', delete=False) as tmp_file:
#         tmp_cpp_file = tmp_file.name
#         tmp_file.write(cpp_code.encode('utf-8'))
    
#     # 2. Create executable name (platform-independent)
#     executable = tmp_cpp_file + ('.exe' if os.name == 'nt' else '')
    
#     try:
#         # 3. Find compiler
#         compiler = shutil.which('g++') or shutil.which('clang++')
#         if not compiler:
#             return [{
#                 "input": "Compiler check",
#                 "output": None,
#                 "expected": None,
#                 "passed": False,
#                 "error": "C++ compiler (g++ or clang++) not found"
#             }]
        
#         # 4. Compile the code
#         compile_proc = await asyncio.create_subprocess_exec(
#             compiler, '-std=c++11', tmp_cpp_file, '-o', executable,
#             stdout=asyncio.subprocess.PIPE,
#             stderr=asyncio.subprocess.PIPE
#         )
        
#         _, stderr = await compile_proc.communicate()
        
#         if compile_proc.returncode != 0:
#             # Compilation error
#             return [{
#                 "input": "Compilation",
#                 "output": None,
#                 "expected": None,
#                 "passed": False,
#                 "error": stderr.decode('utf-8', errors='replace').strip()
#             }]
        
#         # 5. Run the compiled executable
#         run_proc = await asyncio.create_subprocess_exec(
#             executable,
#             stdout=asyncio.subprocess.PIPE,
#             stderr=asyncio.subprocess.PIPE
#         )
        
#         stdout, stderr = await asyncio.wait_for(
#             run_proc.communicate(), 
#             timeout=10.0  # 10 second timeout
#         )
        
#         # 6. Parse results line by line
#         output_lines = stdout.decode('utf-8', errors='replace').strip().split('\n')
        
#         # Track test case index to match with the test_cases list
#         current_test_index = 0
        
#         for line in output_lines:
#             if line.startswith('Test '):
#                 # Parse the test number (1-based)
#                 test_num = int(line.split('Test ')[1].split(':')[0]) - 1
                
#                 # Get the corresponding test case (skip hidden)
#                 visible_test_cases = [t for t in test_cases if not t.get("hidden", False)]
#                 if test_num < len(visible_test_cases):
#                     test_case = visible_test_cases[test_num]
                    
#                     if 'PASS' in line:
#                         results.append({
#                             "input": str(test_case["input"]),
#                             "output": str(test_case["expected_output"]),  # For passing tests, assume output matches expected
#                             "expected": str(test_case["expected_output"]),
#                             "passed": True,
#                             "error": None
#                         })
#                     elif 'FAIL' in line:
#                         # Extract actual output from "Got: X, Expected: Y"
#                         output_part = line.split('Got: ')[1].split(', Expected:')[0].strip() if 'Got:' in line else "Unknown"
                        
#                         results.append({
#                             "input": str(test_case["input"]),
#                             "output": output_part,
#                             "expected": str(test_case["expected_output"]),
#                             "passed": False,
#                             "error": None
#                         })
#                     elif 'ERROR' in line:
#                         error_msg = line.split('ERROR - ')[1] if 'ERROR - ' in line else "Unknown error"
#                         results.append({
#                             "input": str(test_case["input"]),
#                             "output": None,
#                             "expected": str(test_case["expected_output"]),
#                             "passed": False,
#                             "error": error_msg
#                         })
        
#         # If we didn't get any results but the process ran, something went wrong
#         if not results and run_proc.returncode == 0:
#             results.append({
#                 "input": "Output parsing",
#                 "output": None,
#                 "expected": None,
#                 "passed": False,
#                 "error": f"Failed to parse test results. Output: {stdout.decode('utf-8', errors='replace')}"
#             })
        
#     except asyncio.TimeoutError:
#         results.append({
#             "input": "Execution",
#             "output": None,
#             "expected": None,
#             "passed": False,
#             "error": "Execution timed out (10 seconds)"
#         })
#     except Exception as e:
#         results.append({
#             "input": "Error",
#             "output": None,
#             "expected": None,
#             "passed": False,
#             "error": str(e)
#         })
#     finally:
#         # Clean up temporary files
#         try:
#             if os.path.exists(tmp_cpp_file):
#                 os.unlink(tmp_cpp_file)
#             if os.path.exists(executable):
#                 os.unlink(executable)
#         except Exception as e:
#             print(f"Error cleaning up temp files: {e}")
    
#     return results

import os
import json
import tempfile
import asyncio
import shutil

async def run_cpp_code(user_code, func_name, test_cases, standard):
    """
    Run C++ code against test cases and return results.
    """    
    # TODO: Generate a complete C++ program that includes the user's code and test functions
    cpp_code = generate_cpp_program(user_code, func_name, test_cases)

    # TODO: Write the program to a temporary file, compile it, run it, and capture output
    results = await compile_and_run(cpp_code, test_cases, standard)
    # TODO: Return a list of dictionaries containing test results
    return results

def generate_cpp_program(user_code, func_name, test_cases):
    """
    Generate a C++ program with test code.
    """
    
    # TODO: Create test code for each test case
    
    # TODO: Make a program template with proper includes, user code section, and a main function
    
    # TODO: Insert user code and test code into the template and return the complete program

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
            cpp_type = infer_cpp_type(input_val)
            var_name = f"input_{i}_{j}"
            cpp_value = python_to_cpp_value(input_val)
            input_vars.append(f"    {cpp_type} {var_name} = {cpp_value};")
            input_args.append(var_name)

        expected_type = infer_cpp_type(expected)
        expected_var = f"expected_{i}"
        expected_value = python_to_cpp_value(expected)

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

def python_to_cpp_value(value):
    """
    Convert Python values to C++ literals.
    """
    if value is None:
        return "nullptr"
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
        elements = [python_to_cpp_value(item) for item in value]
        return "{" + ", ".join(elements) + "}"
    elif isinstance(value, dict):
        pairs = ["{" + python_to_cpp_value(k) + ", " + python_to_cpp_value(v) + "}" 
                 for k, v in value.items()]
        return "{" + ", ".join(pairs) + "}"
    else:
        return "Warning: Unsupported type!"


def infer_cpp_type(value):
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
            element_type = infer_cpp_type(value[0])
            return f"vector<{element_type}>"
        else:
            return "vector<auto>"  # Not valid C++ but indicates a type issue
    elif isinstance(value, dict):
        if not value:
            return "map<string, int>"  # Default for empty dict
        
        key, val = next(iter(value.items()))
        key_type = infer_cpp_type(key)
        val_type = infer_cpp_type(val)
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

async def compile_and_run(cpp_code, test_cases, standard):
    """
    Compile and run C++ code, then parse the results.
    """
    tmp_cpp_file = None
    executable = None
    results = []
    
    try:
        # TODO: Create a temporary file for the C++ code
        with tempfile.NamedTemporaryFile(suffix='.cpp', delete=False) as tmp_file:
            tmp_cpp_file = tmp_file.name
            tmp_file.write(cpp_code.encode('utf-8'))
        # TODO: Find a C++ compiler (g++ or clang++)
        executable = tmp_cpp_file + ('.exe' if os.name == 'nt' else '')
        compiler = shutil.which("g++") or shutil.which("clang++")
        if not compiler:
            return [{
                    "input": "Compiler check",
                    "output": None,
                    "expected_output": None,
                    "passed": False,
                    "error": "No compiler found."
                }]
        compiler_process = await asyncio.create_subprocess_exec(
            compiler, f'-std={standard}', tmp_cpp_file, '-o', executable, 
            stdout = asyncio.subprocess.PIPE, stderr = asyncio.subprocess.PIPE
        )
        try:
            _, stderr = await asyncio.wait_for(compiler_process.communicate(), timeout=20.0)
            # TODO: Compile the code with appropriate flags
            if compiler_process.returncode != 0:
                # Compiler reached error, return the error
                # TODO: Handle compilation errors Done
                return [{
                        "input": f"{compiler} -std={standard} {tmp_cpp_file} -o {executable}",
                        "output": None,
                        "expected_output": None,
                        "passed": False,
                        "error": stderr.decode('utf-8', errors='replace').strip()
                    }]
        except asyncio.TimeoutError:
            return [{
            "input": f"{compiler} -std={standard} {tmp_cpp_file} -o {executable}",
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
                    actual_output = new1_test[1].split("FAIL - Got: ")[1]
                    expected_output = new1_test[1].split("Expected: ")[1]
                    results.append({"input": {test_cases[test_index]["input"]}, 
                                    "output": actual_output, 
                                    "expected_output": expected_output,
                                    "passed": False,
                                    "error": None})
                elif "ERROR" in test:
                    error1 = new1_test[1].split("ERROR - ")[1]
                    results.append({"input": test_cases[test_index]["input"], 
                                    "output": None, 
                                    "expected_output": test_cases[test_index]['expected_output'],
                                    "passed": False,
                                    "error": error1})
        # TODO: Format results as a list of dictionaries
        
        # TODO: Clean up temporary files
    finally:
        try:
            if tmp_cpp_file is not None and os.path.exists(tmp_cpp_file):
                os.unlink(tmp_cpp_file)
            else:
                return "File never generated"
            if executable is not None and os.path.exists(executable):
                os.unlink(executable)
            else:
                return "Executable never generated."
        except Exception as e:
            print(f"Error cleaning up temp files: {e}")
    return results