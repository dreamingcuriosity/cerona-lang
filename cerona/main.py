import sys

def ifs(lines):
    variables = {}
    functions = {}

    def parse_line(line):
        """Parse a line, handling quotes properly"""
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
            elif char in [' ', '\t'] and not in_quotes:
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
            else:
                current_token += char

        if current_token:
            tokens.append(current_token)

        return tokens

    def resolve_value(token, variables):
        """Resolve a token to its actual value (variable or literal)"""
        if token in variables:
            return variables[token]
        if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
            return token[1:-1]
        return token

    def evaluate_condition(condition_tokens, variables):
        """Evaluate a condition with multiple operators"""
        if len(condition_tokens) < 3:
            return False

        left = resolve_value(condition_tokens[0], variables)
        operator = condition_tokens[1]
        right = resolve_value(condition_tokens[2], variables)

        try:
            left_num = float(left) if isinstance(left, str) and left.replace('.', '', 1).replace('-', '', 1).isdigit() else left
            right_num = float(right) if isinstance(right, str) and right.replace('.', '', 1).replace('-', '', 1).isdigit() else right
        except:
            left_num, right_num = left, right

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

    def find_matching_end(commands, start_index, start_keyword, end_keyword):
        depth = 1
        current_index = start_index + 1
        while current_index < len(commands) and depth > 0:
            if commands[current_index] and commands[current_index][0] == start_keyword:
                depth += 1
            elif commands[current_index] and commands[current_index][0] == end_keyword:
                depth -= 1
            current_index += 1
        return current_index - 1 if depth == 0 else -1

    def call_function(func_name, args, current_variables, all_commands, return_var=None):
        if func_name not in functions:
            print(f"Error: Function '{func_name}' not defined")
            return None
        params, body_commands, func_start_index = functions[func_name]
        local_vars = current_variables.copy()
        for param_name, arg_value in zip(params, args):
            local_vars[param_name] = arg_value
        index = func_start_index + 1
        while index < len(all_commands) and all_commands[index] and all_commands[index][0] != "endfunc":
            cmd = all_commands[index]
            if cmd[0] == "return":
                return resolve_value(cmd[1], local_vars) if len(cmd) > 1 else None
            skip_ahead = execute_single_command(cmd, local_vars, all_commands)
            if skip_ahead is not None:
                index += skip_ahead
            index += 1

    def execute_single_command(i, variables, all_commands):
        """Execute a single command - core interpreter logic"""
        if not i:
            return

        # --- PRINT ---
        if i[0] == "print":
            expr = " ".join(i[1:])
            try:
                result = eval(expr, {"__builtins__": None}, variables)
                print(result)
            except:
                output_parts = []
                for word in i[1:]:
                    output_parts.append(str(variables.get(word, word)))
                print(" ".join(output_parts))

        # --- SET VARIABLE ---
        elif i[0] == "set":
            if len(i) >= 3:
                var_name = i[1]
                value_str = " ".join(i[2:])
                try:
                    variables[var_name] = eval(value_str, {"__builtins__": None}, variables)
                except:
                    variables[var_name] = value_str

        # --- FUNCTION DEFINITIONS ---
        elif i[0] == "func":
            func_name = i[1]
            params = i[2:]
            current_index = all_commands.index(i)
            endfunc_index = find_matching_end(all_commands, current_index, "func", "endfunc")
            if endfunc_index != -1:
                functions[func_name] = (params, all_commands, current_index)
                return endfunc_index - current_index
            else:
                print("Error: Missing endfunc for function", func_name)

        elif i[0] == "call":
            func_name = i[1]
            args = [resolve_value(arg, variables) for arg in i[2:]]
            call_function(func_name, args, variables, all_commands)

        # --- CONTROL FLOW: IF STATEMENTS ---
        elif i[0] == "if":
            # Check if it's a single-line if with "then"
            if "then" in i:
                then_index = i.index("then")
                condition_tokens = i[1:then_index]
                command_tokens = i[then_index + 1:]
                if evaluate_condition(condition_tokens, variables):
                    for cmd in " ".join(command_tokens).split(";"):
                        cmd_tokens = parse_line(cmd.strip())
                        execute_single_command(cmd_tokens, variables, all_commands)
            else:
                # Multi-line if block
                current_index = all_commands.index(i)
                
                # Find else and endif positions
                else_index = None
                endif_index = None
                depth = 1
                search_index = current_index + 1
                
                while search_index < len(all_commands) and depth > 0:
                    cmd = all_commands[search_index]
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
                    print("Error: Missing endif")
                    return
                
                # Extract condition (everything after "if")
                condition_tokens = i[1:]
                condition_met = evaluate_condition(condition_tokens, variables)
                
                if condition_met:
                    # Execute if block (from current+1 to else or endif)
                    end_of_block = else_index if else_index else endif_index
                    block_index = current_index + 1
                    while block_index < end_of_block:
                        cmd = all_commands[block_index]
                        skip = execute_single_command(cmd, variables, all_commands)
                        if skip is not None:
                            block_index += skip
                        block_index += 1
                elif else_index is not None:
                    # Execute else block (from else+1 to endif)
                    block_index = else_index + 1
                    while block_index < endif_index:
                        cmd = all_commands[block_index]
                        skip = execute_single_command(cmd, variables, all_commands)
                        if skip is not None:
                            block_index += skip
                        block_index += 1
                
                # Skip to after endif
                return endif_index - current_index

        # --- WHILE LOOP ---
        elif i[0] == "while":
            current_index = all_commands.index(i)
            endwhile_index = find_matching_end(all_commands, current_index, "while", "endwhile")
            
            if endwhile_index == -1:
                print("Error: Missing endwhile")
                return
            
            condition_tokens = i[1:]
            
            while evaluate_condition(condition_tokens, variables):
                loop_index = current_index + 1
                while loop_index < endwhile_index:
                    cmd = all_commands[loop_index]
                    skip = execute_single_command(cmd, variables, all_commands)
                    if skip is not None:
                        loop_index += skip
                    loop_index += 1
            
            return endwhile_index - current_index

        # --- FOR LOOP ---
        elif i[0] == "for":
            current_index = all_commands.index(i)
            endfor_index = find_matching_end(all_commands, current_index, "for", "endfor")
            
            if endfor_index == -1:
                print("Error: Missing endfor")
                return
            
            if len(i) < 4 or i[2] != "in":
                print("Error: Invalid for loop syntax")
                return
            
            var_name = i[1]
            
            if len(i) == 5:
                try:
                    start = int(resolve_value(i[3], variables))
                    end = int(resolve_value(i[4], variables))
                    iterable = range(start, end)
                except ValueError:
                    print("Error: For loop range must be integers")
                    return
            elif len(i) == 4:
                iterable_value = resolve_value(i[3], variables)
                
                if isinstance(iterable_value, str):
                    try:
                        iterable = eval(iterable_value, {"__builtins__": None}, variables)
                    except:
                        iterable = iterable_value
                else:
                    iterable = iterable_value
            else:
                print("Error: Invalid for loop syntax")
                return
            
            for value in iterable:
                variables[var_name] = value
                
                loop_index = current_index + 1
                while loop_index < endfor_index:
                    cmd = all_commands[loop_index]
                    skip = execute_single_command(cmd, variables, all_commands)
                    if skip is not None:
                        loop_index += skip
                    loop_index += 1
            
            return endfor_index - current_index

        elif i[0] == "input":
            prompt = " ".join(i[2:]) if len(i) > 2 else ""
            variables[i[1]] = input(prompt)

        # --- UNKNOWN COMMAND: TRY TO EVALUATE AS EXPRESSION ---
        else:
            expr = " ".join(i)
            try:
                result = eval(expr, {"__builtins__": None}, variables)
                print(result)
            except Exception:
                print(f"Unknown command: {i[0]}")

    # --- PARSE LINES ---
    cleaned = [parse_line(line.strip()) for line in lines.split("\n") if line.strip()]

    # --- EXECUTE LINES ---
    index = 0
    while index < len(cleaned):
        i = cleaned[index]
        skip_ahead = execute_single_command(i, variables, cleaned)
        if skip_ahead is not None:
            index += skip_ahead
        index += 1


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
        print(f"File '{filename}' not found.")
        sys.exit(1)

    ifs(lines)


if __name__ == "__main__":
    main()
