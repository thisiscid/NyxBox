# Yes, C++ was so complex I needed a seperate file to put it all in. Java will probably be the same.

import os
import json
import tempfile
import asyncio
import shutil
import re

ALLOWED_CPP_HEADERS = {
    "vector", "string", "algorithm", "unordered_map",
    "unordered_set", "map", "set", "queue", "stack",
    "iostream", 
}

async def run_cpp_code(user_code, func_name, test_cases, standard, is_submission=False, is_guest = False):
    """
    Run C++ code against test cases and return results.
    """    
    if is_guest:
        imports = re.findall(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', user_code, re.MULTILINE)
        for imp in imports:
            if not any(imp.startswith(prefix) for prefix in ALLOWED_CPP_HEADERS):
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
    cpp_code = generate_cpp_program(user_code, func_name, filtered_tests, is_submission)

    results = await compile_and_run(cpp_code, filtered_tests, standard)
    return results

def generate_cpp_program(user_code, func_name, test_cases, is_submission):
    """
    Generate a C++ program with test code.
    """
    
    test_code = generate_test_code(func_name, test_cases, is_submission)
    program_template = """
#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <set>
#include <unordered_set>
#include <unordered_map>
#include <stdexcept>
using namespace std;

// Helper to print STL containers for test output
template <typename T>
std::ostream& operator<<(std::ostream& os, const std::vector<T>& vec) {{
    os << "[";
    for (size_t i = 0; i < vec.size(); ++i) {{
        if (i > 0) os << ", ";
        os << vec[i];
    }}
    os << "]";
    return os;
}}

template <typename T>
std::ostream& operator<<(std::ostream& os, const std::set<T>& s) {{
    os << "{{";
    size_t i = 0;
    for (const auto& item : s) {{
        if (i++ > 0) os << ", ";
        os << item;
    }}
    os << "}}";
    return os;
}}

template <typename T>
std::ostream& operator<<(std::ostream& os, const std::unordered_set<T>& s) {{
    os << "{{";
    size_t i = 0;
    for (const auto& item : s) {{
        if (i++ > 0) os << ", ";
        os << item;
    }}
    os << "}}";
    return os;
}}

template <typename K, typename V>
std::ostream& operator<<(std::ostream& os, const std::map<K, V>& m) {{
    os << "{{";
    size_t i = 0;
    for (const auto& kv : m) {{
        if (i++ > 0) os << ", ";
        os << kv.first << ": " << kv.second;
    }}
    os << "}}";
    return os;
}}

template <typename K, typename V>
std::ostream& operator<<(std::ostream& os, const std::unordered_map<K, V>& m) {{
    os << "{{";
    size_t i = 0;
    for (const auto& kv : m) {{
        if (i++ > 0) os << ", ";
        os << kv.first << ": " << kv.second;
    }}
    os << "}}";
    return os;
}}

template <typename A, typename B>
std::ostream& operator<<(std::ostream& os, const std::pair<A, B>& p) {{
    os << "(" << p.first << ", " << p.second << ")";
    return os;
}}

// ===== USER CODE START =====
{user_code}
// ===== USER CODE END =====

int main() {{
    bool all_passed = true;

{test_code}

    cout << (all_passed ? "ALL TESTS PASSED" : "SOME TESTS FAILED") << endl;
    return all_passed ? 0 : 1;
}}
"""
    ret = program_template.format(user_code=user_code, test_code=test_code)
    return ret
def generate_test_code(func_name, test_cases, is_submission):
    """
    Generate C++ code that tests the user's function.
    """
    test_code_blocks=[]    
    for i, test in enumerate(test_cases):
        if not is_submission and test.get("hidden", False):
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
   
async def compile_and_run(cpp_code, test_cases, standard):
    """
    Compile and run C++ code, then parse the results.
    """
    tmp_cpp_file = None
    executable = None
    results = []
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.cpp', delete=False) as tmp_file:
            tmp_cpp_file = tmp_file.name
            tmp_file.write(cpp_code.encode('utf-8'))
        executable = tmp_cpp_file.strip(".cpp") + ('out.exe' if os.name == 'nt' else 'out')
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
            if compiler_process.returncode != 0:
                # Compiler reached error, return the error
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

    finally:
        try:
            if tmp_cpp_file is not None and os.path.exists(tmp_cpp_file):
                os.unlink(tmp_cpp_file)
            if tmp_cpp_file is not None and os.path.exists(tmp_cpp_file):
                os.unlink(tmp_cpp_file)
        except Exception as e:
            print(f"Error cleaning up temp files: {e}")
    return results