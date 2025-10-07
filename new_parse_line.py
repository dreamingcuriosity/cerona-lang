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
