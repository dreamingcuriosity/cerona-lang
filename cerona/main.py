import sys

class CeronaError(Exception):
    """Base exception for Cerona errors"""
    def __init__(self, message, line_num=None, line_content=None, col=None):
        self.message = message
        self.line_num = line_num
        self.line_content = line_content
        self.col = col
        super().__init__(self.format_error())

    def format_error(self):
        """Format error in GCC-style"""
        if self.line_num is None:
            return f"error: {self.message}"

        error_msg = f"error at line {self.line_num}: {self.message}\n"
        if self.line_content:
            error_msg += f"  {self.line_num} | {self.line_content}\n"
            if self.col is not None:
                error_msg += f"     | {' ' * self.col}^\n"
        return error_msg


class CeronaClass:
    """Represents a class definition in Cerona"""
    def __init__(self, name, attributes, methods, line_num):
        self.name = name
        self.attributes = attributes
        self.methods = methods
        self.line_num = line_num


class CeronaObject:
    """Represents an instance of a Cerona class"""
    def __init__(self, class_def, instance_vars):
        self.class_def = class_def
        self.instance_vars = instance_vars.copy()

    def get_attr(self, attr_name):
        return self.instance_vars.get(attr_name)

    def set_attr(self, attr_name, value):
        self.instance_vars[attr_name] = value


def find_matching_end(commands, start_index, start_keyword, end_keyword):
    """Find the matching end keyword for a block structure"""
    depth = 1
    search_index = start_index + 1

    while search_index < len(commands) and depth > 0:
        ln, cmd = commands[search_index]
        if cmd and cmd[0] == start_keyword:
            depth += 1
        elif cmd and cmd[0] == end_keyword:
            depth -= 1
            if depth == 0:
                return search_index
        search_index += 1

    return -1


def ifs(lines, filename="<input>"):
    variables = {}
    functions = {}
    classes = {}
    objects = {}

    # Store original lines for error reporting
    original_lines = lines.split("\n")

    def parse_line(line, line_num):
        """Parse a line, handling quotes properly and stripping parentheses"""
        try:
            comment_index = -1
            in_quotes = False
            quote_char = None

            for idx, char in enumerate(line):
                if char in ['"', "'"]:
                    if not in_quotes:
                        in_quotes = True
                        quote_char = char
                    elif char == quote_char:
                        in_quotes = False
                        quote_char = None
                elif char == '#' and not in_quotes:
                    comment_index = idx
                    break

            if comment_index != -1:
                line = line[:comment_index]

            line = line.strip()
            if not line:
                return []

            # Strip leading/trailing parentheses before tokenizing
            while line.startswith('(') and line.endswith(')'):
                line = line[1:-1].strip()

            tokens = []
            current_token = ""
            in_quotes = False
            quote_char = None
            escape_next = False

            for char in line:
                if escape_next:
                    current_token += char
                    escape_next = False
                elif char == '\\':
                    escape_next = True
                elif char in ['"', "'"]:
                    if not in_quotes:
                        in_quotes = True
                        quote_char = char
                        if current_token.strip():
                            tokens.extend(current_token.strip().split())
                        current_token = ""
                    elif char == quote_char:
                        in_quotes = False
                        quote_char = None
                        tokens.append(current_token)
                        current_token = ""
                    else:
                        current_token += char
                elif char in ['(', ')'] and not in_quotes:
                    # Skip parentheses when not in quotes
                    if current_token:
                        tokens.append(current_token)
                        current_token = ""
                elif char in [' ', '\t'] and not in_quotes:
                    if current_token:
                        tokens.append(current_token)
                        current_token = ""
                else:
                    current_token += char

            if current_token:
                tokens.append(current_token)

            if in_quotes:
                raise CeronaError(
                    f"unterminated string literal",
                    line_num,
                    original_lines[line_num - 1] if line_num <= len(original_lines) else line
                )

            return tokens
        except CeronaError:
            raise
        except Exception as e:
            raise CeronaError(
                f"parse error: {str(e)}",
                line_num,
                original_lines[line_num - 1] if line_num <= len(original_lines) else line
            )

    def resolve_value(token, variables, line_num=None):
        """Resolve a token to its actual value (variable or literal)"""
        if token in variables:
            return variables[token]
        if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
            return token[1:-1]
        return token

    def evaluate_condition(condition_tokens, variables, line_num=None):
        """Evaluate a condition with multiple operators"""
        if len(condition_tokens) < 3:
            raise CeronaError(
                f"invalid condition: expected at least 3 tokens, got {len(condition_tokens)}",
                line_num,
                original_lines[line_num - 1] if line_num and line_num <= len(original_lines) else None
            )

        left = resolve_value(condition_tokens[0], variables, line_num)
        operator = condition_tokens[1]
        right = resolve_value(condition_tokens[2], variables, line_num)

        try:
            left_num = float(left) if isinstance(left, str) and left.replace('.', '', 1).replace('-', '', 1).isdigit() else left
            right_num = float(right) if isinstance(right, str) and right.replace('.', '', 1).replace('-', '', 1).isdigit() else right
        except:
            left_num, right_num = left, right

        valid_operators = ["equals", "==", "notequals", "!=", "greater", ">",
                          "greaterequals", ">=", "less", "<", "lessequals", "<=",
                          "contains", "in"]

        if operator not in valid_operators:
            raise CeronaError(
                f"unknown operator '{operator}' (valid: {', '.join(valid_operators)})",
                line_num,
                original_lines[line_num - 1] if line_num and line_num <= len(original_lines) else None
            )

        if operator in ["equals", "=="]:
            return str(left) == str(right)
        elif operator in ["notequals", "!="]:
            return str(left) != str(right)
        elif operator in ["greater", ">"]:
            return left_num > right_num
        elif operator in ["greaterequals", ">="]:
            return left_num >= right_num
        elif operator in ["less", "<"]:
            return left_num < right_num
        elif operator in ["lessequals", "<="]:
            return left_num <= right_num
        elif operator == "contains":
            return str(right) in str(left)
        elif operator == "in":
            return str(left) in str(right)

        return False

    def call_function(func_name, args, scope, all_commands):
        """Call a user-defined function"""
        if func_name not in functions:
            raise CeronaError(f"undefined function '{func_name}'")

        params, commands, func_line_num = functions[func_name]

        if len(args) != len(params):
            raise CeronaError(
                f"function '{func_name}' expects {len(params)} arguments, got {len(args)}"
            )

        # Create function scope
        func_scope = scope.copy()
        for param, arg in zip(params, args):
            func_scope[param] = arg

        # Execute function body
        current_index = next((idx for idx, (ln, cmd) in enumerate(commands) if ln == func_line_num), -1)
        endfunc_index = find_matching_end(commands, current_index, "func", "endfunc")

        if endfunc_index != -1:
            body_index = current_index + 1
            while body_index < endfunc_index:
                ln, cmd = commands[body_index]
                skip = execute_single_command(ln, cmd, func_scope, commands)
                if skip is not None:
                    body_index += skip
                body_index += 1

    def call_method(obj, method_name, args, all_commands):
        """Call a method on an object"""
        if method_name not in obj.class_def.methods:
            raise CeronaError(
                f"method '{method_name}' not found in class '{obj.class_def.name}'"
            )

        params, commands, func_line_num = obj.class_def.methods[method_name]

        if len(args) != len(params):
            raise CeronaError(
                f"method '{method_name}' expects {len(args)} arguments, got {len(args)}"
            )

        # Create method scope with instance variables
        method_scope = obj.instance_vars.copy()
        method_scope.update(variables)

        for param, arg in zip(params, args):
            method_scope[param] = arg

        # Execute method body
        current_index = next((idx for idx, (ln, cmd) in enumerate(commands) if ln == func_line_num), -1)
        endfunc_index = find_matching_end(commands, current_index, "func", "endfunc")

        if endfunc_index != -1:
            body_index = current_index + 1
            while body_index < endfunc_index:
                ln, cmd = commands[body_index]
                skip = execute_single_command(ln, cmd, method_scope, commands)
                if skip is not None:
                    body_index += skip
                body_index += 1

        # Update instance variables from method scope
        for key in obj.instance_vars.keys():
            if key in method_scope:
                obj.instance_vars[key] = method_scope[key]

    def execute_single_command(line_num, i, variables, all_commands):
        """Execute a single command - core interpreter logic"""
        if not i:
            return

        try:
            # --- SET VARIABLE ---
            if i[0] == "set":
                if len(i) < 3:
                    raise CeronaError(
                        "set requires variable name and value",
                        line_num,
                        original_lines[line_num - 1] if line_num <= len(original_lines) else None
                    )

                var_name = i[1]
                expr = " ".join(i[2:])

                # Try to evaluate as expression
                try:
                    variables[var_name] = eval(expr, {"__builtins__": None}, variables)
                except:
                    # If eval fails, try to resolve and then store
                    resolved = resolve_value(expr, variables, line_num)
                    # Check if resolved value is a string that looks like an expression
                    if isinstance(resolved, str) and any(op in resolved for op in ['+', '-', '*', '/', '%']):
                        try:
                            variables[var_name] = eval(resolved, {"__builtins__": None}, variables)
                        except:
                            variables[var_name] = resolved
                    else:
                        variables[var_name] = resolved

            # Replace the print section in execute_single_command (around line 281)

            # --- PRINT ---
            elif i[0] == "print":
                if len(i) < 2:
                    raise CeronaError("print requires at least one argument", line_num)

                # Join all tokens after "print"
                expr = " ".join(i[1:])
    
                # First, try to evaluate as expression with current scope
                try:
                    result = eval(expr,  variables)
                    print(result)
                    return
                except:
                    pass
    
                # If that fails, try direct variable lookup
                if expr in variables:
                    print(variables[expr])
                    return
    
                # Check object attributes
                for obj in objects.values():
                    if expr in obj.instance_vars:
                        print(obj.instance_vars[expr])
                        return
    
                # If all else fails, print as literal
                print(expr)
            # --- CLASS DEFINITION ---
            elif i[0] == "class":
                if len(i) < 2:
                    raise CeronaError(
                        "class requires class name",
                        line_num,
                        original_lines[line_num - 1] if line_num <= len(original_lines) else None
                    )

                class_name = i[1]
                current_index = next((idx for idx, (ln, cmd) in enumerate(all_commands) if ln == line_num), -1)
                endclass_index = find_matching_end(all_commands, current_index, "class", "endclass")

                if endclass_index == -1:
                    raise CeronaError(
                        f"missing 'endclass' for class '{class_name}'",
                        line_num,
                        original_lines[line_num - 1] if line_num <= len(original_lines) else None
                    )

                # Parse class body
                attributes = {}
                methods = {}
                class_index = current_index + 1

                while class_index < endclass_index:
                    ln, cmd = all_commands[class_index]

                    if cmd[0] == "set":
                        # Class attribute
                        if len(cmd) >= 3:
                            attr_name = cmd[1]
                            attr_value = " ".join(cmd[2:])
                            try:
                                attributes[attr_name] = eval(attr_value, {"__builtins__": None}, {})
                            except:
                                attributes[attr_name] = attr_value

                    elif cmd[0] == "func":
                        # Class method
                        if len(cmd) < 2:
                            raise CeronaError(
                                "func requires function name",
                                ln,
                                original_lines[ln - 1] if ln <= len(original_lines) else None
                            )

                        method_name = cmd[1]
                        params = cmd[2:]

                        # Find matching endfunc
                        endfunc_index = find_matching_end(all_commands, class_index, "func", "endfunc")
                        if endfunc_index == -1:
                            raise CeronaError(
                                f"missing 'endfunc' for method '{method_name}'",
                                ln,
                                original_lines[ln - 1] if ln <= len(original_lines) else None
                            )

                        # Store method definition
                        methods[method_name] = (params, all_commands, ln)
                        class_index = endfunc_index

                    class_index += 1

                # Store class definition
                classes[class_name] = CeronaClass(class_name, attributes, methods, line_num)

                return endclass_index - current_index

            # --- CREATE OBJECT INSTANCE ---
            elif i[0] == "new":
                if len(i) < 3:
                    raise CeronaError(
                        "new requires class name and instance name",
                        line_num,
                        original_lines[line_num - 1] if line_num <= len(original_lines) else None
                    )

                class_name = i[1]
                instance_name = i[2]
                args = [resolve_value(arg, variables, line_num) for arg in i[3:]]

                if class_name not in classes:
                    raise CeronaError(
                        f"undefined class '{class_name}'",
                        line_num,
                        original_lines[line_num - 1] if line_num <= len(original_lines) else None
                    )

                class_def = classes[class_name]

                # Create instance with default attributes
                obj = CeronaObject(class_def, class_def.attributes)
                objects[instance_name] = obj

                # Call init method if it exists
                if "init" in class_def.methods:
                    call_method(obj, "init", args, all_commands)

            # --- FUNCTION DEFINITIONS ---
            elif i[0] == "func":
                if len(i) < 2:
                    raise CeronaError(
                        "func requires function name",
                        line_num,
                        original_lines[line_num - 1] if line_num <= len(original_lines) else None
                    )
                func_name = i[1]
                params = i[2:]
                current_index = next((idx for idx, (ln, cmd) in enumerate(all_commands) if ln == line_num), -1)
                if current_index == -1:
                    raise CeronaError("internal error: could not find current command", line_num)

                endfunc_index = find_matching_end(all_commands, current_index, "func", "endfunc")
                if endfunc_index != -1:
                    functions[func_name] = (params, all_commands, line_num)
                    return endfunc_index - current_index
                else:
                    raise CeronaError(
                        f"missing 'endfunc' for function '{func_name}'",
                        line_num,
                        original_lines[line_num - 1] if line_num <= len(original_lines) else None
                    )

            elif i[0] == "call":
                if len(i) < 2:
                    raise CeronaError(
                        "call requires function name",
                        line_num,
                        original_lines[line_num - 1] if line_num <= len(original_lines) else None
                    )

                # Check if it's a method call (obj.method)
                if "." in i[1]:
                    parts = i[1].split(".", 1)
                    obj_name = parts[0]
                    method_name = parts[1]

                    if obj_name not in objects:
                        raise CeronaError(
                            f"undefined object '{obj_name}'",
                            line_num,
                            original_lines[line_num - 1] if line_num <= len(original_lines) else None
                        )

                    args = [resolve_value(arg, variables, line_num) for arg in i[2:]]
                    call_method(objects[obj_name], method_name, args, all_commands)
                else:
                    # Regular function call
                    func_name = i[1]
                    args = [resolve_value(arg, variables, line_num) for arg in i[2:]]
                    call_function(func_name, args, variables, all_commands)

            # --- CONTROL FLOW: IF STATEMENTS ---
            elif i[0] == "if":
                if "then" in i:
                    then_index = i.index("then")
                    condition_tokens = i[1:then_index]
                    command_tokens = i[then_index + 1:]
                    if evaluate_condition(condition_tokens, variables, line_num):
                        for cmd in " ".join(command_tokens).split(";"):
                            cmd_tokens = parse_line(cmd.strip(), line_num)
                            execute_single_command(line_num, cmd_tokens, variables, all_commands)
                else:
                    current_index = next((idx for idx, (ln, cmd) in enumerate(all_commands) if ln == line_num), -1)
                    else_index = None
                    endif_index = None
                    depth = 1
                    search_index = current_index + 1

                    while search_index < len(all_commands) and depth > 0:
                        ln, cmd = all_commands[search_index]
                        if cmd and cmd[0] == "if":
                            depth += 1
                        elif cmd and cmd[0] == "endif":
                            depth -= 1
                            if depth == 0:
                                endif_index = search_index
                        elif cmd and cmd[0] == "else" and depth == 1:
                            else_index = search_index
                        search_index += 1

                    if endif_index == -1:
                        raise CeronaError(
                            "missing 'endif' for if statement",
                            line_num,
                            original_lines[line_num - 1] if line_num <= len(original_lines) else None
                        )

                    condition_tokens = i[1:]
                    condition_met = evaluate_condition(condition_tokens, variables, line_num)

                    if condition_met:
                        end_of_block = else_index if else_index else endif_index
                        block_index = current_index + 1
                        while block_index < end_of_block:
                            ln, cmd = all_commands[block_index]
                            skip = execute_single_command(ln, cmd, variables, all_commands)
                            if skip is not None:
                                block_index += skip
                            block_index += 1
                    elif else_index is not None:
                        block_index = else_index + 1
                        while block_index < endif_index:
                            ln, cmd = all_commands[block_index]
                            skip = execute_single_command(ln, cmd, variables, all_commands)
                            if skip is not None:
                                block_index += skip
                            block_index += 1

                    return endif_index - current_index

            # --- WHILE LOOP ---
            elif i[0] == "while":
                current_index = next((idx for idx, (ln, cmd) in enumerate(all_commands) if ln == line_num), -1)
                endwhile_index = find_matching_end(all_commands, current_index, "while", "endwhile")

                if endwhile_index == -1:
                    raise CeronaError(
                        "missing 'endwhile' for while loop",
                        line_num,
                        original_lines[line_num - 1] if line_num <= len(original_lines) else None
                    )

                condition_tokens = i[1:]

                while evaluate_condition(condition_tokens, variables, line_num):
                    loop_index = current_index + 1
                    while loop_index < endwhile_index:
                        ln, cmd = all_commands[loop_index]
                        skip = execute_single_command(ln, cmd, variables, all_commands)
                        if skip is not None:
                            loop_index += skip
                        loop_index += 1

                return endwhile_index - current_index

            # --- FOR LOOP ---
            elif i[0] == "for":
                current_index = next((idx for idx, (ln, cmd) in enumerate(all_commands) if ln == line_num), -1)
                endfor_index = find_matching_end(all_commands, current_index, "for", "endfor")

                if endfor_index == -1:
                    raise CeronaError(
                        "missing 'endfor' for for loop",
                        line_num,
                        original_lines[line_num - 1] if line_num <= len(original_lines) else None
                    )

                if len(i) < 4 or i[2] != "in":
                    raise CeronaError(
                        "invalid for loop syntax (expected: for VAR in ITERABLE)",
                        line_num,
                        original_lines[line_num - 1] if line_num <= len(original_lines) else None
                    )

                var_name = i[1]

                if len(i) == 5:
                    try:
                        start = int(resolve_value(i[3], variables, line_num))
                        end = int(resolve_value(i[4], variables, line_num))
                        iterable = range(start, end)
                    except ValueError:
                        raise CeronaError(
                            "for loop range bounds must be integers",
                            line_num,
                            original_lines[line_num - 1] if line_num <= len(original_lines) else None
                        )
                elif len(i) == 4:
                    iterable_value = resolve_value(i[3], variables, line_num)
                    if isinstance(iterable_value, str):
                        try:
                            iterable = eval(iterable_value, {"__builtins__": None}, variables)
                        except:
                            iterable = iterable_value
                    else:
                        iterable = iterable_value
                else:
                    raise CeronaError(
                        "invalid for loop syntax",
                        line_num,
                        original_lines[line_num - 1] if line_num <= len(original_lines) else None
                    )

                for value in iterable:
                    variables[var_name] = value
                    loop_index = current_index + 1
                    while loop_index < endfor_index:
                        ln, cmd = all_commands[loop_index]
                        skip = execute_single_command(ln, cmd, variables, all_commands)
                        if skip is not None:
                            loop_index += skip
                        loop_index += 1

                return endfor_index - current_index

            elif i[0] == "input":
                if len(i) < 2:
                    raise CeronaError(
                        "input requires variable name",
                        line_num,
                        original_lines[line_num - 1] if line_num <= len(original_lines) else None
                    )
                prompt = " ".join(i[2:]) if len(i) > 2 else ""
                variables[i[1]] = input(prompt)

            # --- UNKNOWN COMMAND ---
            else:
                expr = " ".join(i)
                try:
                    result = eval(expr, {"__builtins__": None}, variables)
                    print(result)
                except Exception:
                    raise CeronaError(
                        f"unknown command '{i[0]}'",
                        line_num,
                        original_lines[line_num - 1] if line_num <= len(original_lines) else None
                    )

        except CeronaError:
            raise
        except Exception as e:
            raise CeronaError(
                f"runtime error: {str(e)}",
                line_num,
                original_lines[line_num - 1] if line_num <= len(original_lines) else None
            )

    # --- PARSE LINES WITH LINE NUMBERS ---
    cleaned = []
    for line_num, line in enumerate(original_lines, start=1):
        stripped = line.strip()
        if stripped:
            try:
                tokens = parse_line(stripped, line_num)
                if tokens:
                    cleaned.append((line_num, tokens))
            except CeronaError as e:
                print(f"{filename}:{e}", file=sys.stderr)
                sys.exit(1)

    # --- EXECUTE LINES ---
    index = 0
    try:
        while index < len(cleaned):
            line_num, i = cleaned[index]
            skip_ahead = execute_single_command(line_num, i, variables, cleaned)
            if skip_ahead is not None:
                index += skip_ahead
            index += 1
    except CeronaError as e:
        print(f"{filename}:{e}", file=sys.stderr)
        sys.exit(1)

def execute(code: str):
    """Execute Cerona source code directly from a string."""
    return ifs(code)

def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m cerona.main <filename>")
        sys.exit(1)

    filename = sys.argv[1]
    try:
        with open(filename, 'r') as file:
            lines = file.read()
    except FileNotFoundError:
        print(f"{filename}: error: file not found", file=sys.stderr)
        sys.exit(1)

    ifs(lines, filename)

if __name__ == "__main__":
    main()
