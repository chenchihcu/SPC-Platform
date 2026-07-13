import os
import ast
import json
import re

class CodebaseBugScanner(ast.NodeVisitor):
    def __init__(self, filepath, relative_path, is_production=True):
        self.filepath = filepath
        self.relative_path = relative_path
        self.is_production = is_production
        self.bugs = []
        self.source_lines = []
        self.try_depth = 0
        self.except_depth = 0
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                self.source_lines = f.readlines()
        except Exception:
            pass

    def _get_line_content(self, lineno):
        if 0 < lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1].strip()
        return ""

    def scan_comments(self):
        # Scan for TODO, FIXME, BUG, HACK comments
        comment_pattern = re.compile(r'#\s*(TODO|FIXME|BUG|HACK)(.*)', re.IGNORECASE)
        for idx, line in enumerate(self.source_lines):
            match = comment_pattern.search(line)
            if match:
                tag = match.group(1).upper()
                detail = match.group(2).strip()
                self.bugs.append({
                    "file": self.relative_path,
                    "line": idx + 1,
                    "type": f"Comment Tag: {tag}",
                    "severity": "Medium" if tag in ('FIXME', 'BUG') else "Low",
                    "description": f"Found unresolved comment tag '{tag}': {detail}",
                    "code": line.strip()
                })

    def visit_FunctionDef(self, node):
        # 1. Check for mutable default arguments
        for default in node.args.defaults:
            is_mutable = False
            desc = ""
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                is_mutable = True
                desc = "List/Dict/Set literal default value"
            elif isinstance(default, ast.Call):
                if isinstance(default.func, ast.Name) and default.func.id in ('list', 'dict', 'set'):
                    is_mutable = True
                    desc = "Call to list()/dict()/set() default value"
            
            if is_mutable:
                self.bugs.append({
                    "file": self.relative_path,
                    "line": default.lineno,
                    "type": "Mutable Default Argument",
                    "severity": "High",
                    "description": f"Function '{node.name}' has mutable default argument ({desc}). This can lead to shared state across calls.",
                    "code": self._get_line_content(default.lineno)
                })
        
        self.generic_visit(node)

    def visit_Try(self, node):
        # 2. Check for bare except or empty/silent exception handlers
        for handler in node.handlers:
            # Bare except
            if handler.type is None:
                does_nothing = False
                if len(handler.body) == 1:
                    body_node = handler.body[0]
                    if isinstance(body_node, ast.Pass):
                        does_nothing = True
                    elif isinstance(body_node, ast.Expr) and isinstance(body_node.value, ast.Constant) and body_node.value.value is Ellipsis:
                        does_nothing = True
                
                self.bugs.append({
                    "file": self.relative_path,
                    "line": handler.lineno,
                    "type": "Bare Except" if not does_nothing else "Bare Except with Silent Pass",
                    "severity": "High" if not does_nothing else "Critical",
                    "description": "Bare except clause catches all exceptions including SystemExit and KeyboardInterrupt.",
                    "code": self._get_line_content(handler.lineno)
                })
            else:
                is_general = False
                if isinstance(handler.type, ast.Name) and handler.type.id in ('Exception', 'BaseException'):
                    is_general = True
                
                if is_general:
                    does_nothing = False
                    if len(handler.body) == 1:
                        body_node = handler.body[0]
                        if isinstance(body_node, ast.Pass):
                            does_nothing = True
                        elif isinstance(body_node, ast.Expr) and isinstance(body_node.value, ast.Constant) and body_node.value.value is Ellipsis:
                            does_nothing = True
                    
                    if does_nothing:
                        self.bugs.append({
                            "file": self.relative_path,
                            "line": handler.lineno,
                            "type": "Silent Exception Handler",
                            "severity": "Medium",
                            "description": "Catching general Exception and ignoring it with a bare 'pass'. May hide critical bugs.",
                            "code": self._get_line_content(handler.lineno)
                        })
        
        self.try_depth += 1
        
        # Traverse body with try_depth
        for item in node.body:
            self.visit(item)
            
        # Traverse handlers with except_depth
        self.except_depth += 1
        for handler in node.handlers:
            self.visit(handler)
        self.except_depth -= 1
        
        for orelse in node.orelse:
            self.visit(orelse)
        for finalbody in node.finalbody:
            self.visit(finalbody)
            
        self.try_depth -= 1

    def visit_Compare(self, node):
        # 3. Check for float comparisons using == or !=
        is_float_compare = False
        for op in node.ops:
            if isinstance(op, (ast.Eq, ast.NotEq)):
                comparators = [node.left] + node.comparators
                for comp in comparators:
                    if isinstance(comp, ast.Constant) and isinstance(comp.value, float):
                        is_float_compare = True
                        break
        
        if is_float_compare:
            self.bugs.append({
                "file": self.relative_path,
                "line": node.lineno,
                "type": "Float Equality Comparison",
                "severity": "Medium",
                "description": "Direct equality comparison with a float literal. Floating-point precision issues may cause unexpected results.",
                "code": self._get_line_content(node.lineno)
            })
        
        self.generic_visit(node)

    def visit_Call(self, node):
        # 4. Check for potential unparameterized SQL queries in DB operations
        is_db_execute = False
        if isinstance(node.func, ast.Attribute) and node.func.attr in ('execute', 'executemany'):
            is_db_execute = True
        
        if is_db_execute and len(node.args) > 0:
            sql_arg = node.args[0]
            has_formatted_string = False
            desc = ""
            
            if isinstance(sql_arg, ast.JoinedStr):
                has_formatted_string = True
                desc = "f-string formatting"
            elif isinstance(sql_arg, ast.BinOp) and isinstance(sql_arg.op, ast.Mod):
                has_formatted_string = True
                desc = "% operator formatting"
            elif isinstance(sql_arg, ast.Call) and isinstance(sql_arg.func, ast.Attribute) and sql_arg.func.attr == "format":
                has_formatted_string = True
                desc = ".format() string method"
            
            if has_formatted_string:
                self.bugs.append({
                    "file": self.relative_path,
                    "line": sql_arg.lineno,
                    "type": "SQL Injection Risk / Query Formatting",
                    "severity": "High",
                    "description": f"Database execution with formatted SQL query string ({desc}). Use parameterized queries instead.",
                    "code": self._get_line_content(sql_arg.lineno)
                })
        
        # 6. Use of raw print in production code
        if self.is_production and isinstance(node.func, ast.Name) and node.func.id == 'print':
            self.bugs.append({
                "file": self.relative_path,
                "line": node.lineno,
                "type": "Production Print Statement",
                "severity": "Low",
                "description": "Raw print statement used in production code. Prefer logging module.",
                "code": self._get_line_content(node.lineno)
            })
            
        # 7. Unhandled json.load or json.loads
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == 'json' and node.func.attr in ('load', 'loads'):
            if self.try_depth == 0:
                self.bugs.append({
                    "file": self.relative_path,
                    "line": node.lineno,
                    "type": "Unhandled JSON Load",
                    "severity": "Medium",
                    "description": "Calling json.load/loads outside of a try-except block. Unhandled JSONDecodeError if input is malformed.",
                    "code": self._get_line_content(node.lineno)
                })
                
        # 9. Numpy/Pandas Potential NaN/Inf Propagation
        is_stat_call = False
        stat_desc = ""
        # Check np.mean, np.std, np.var, np.min, np.max, np.median
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id in ('np', 'numpy'):
            if node.func.attr in ('mean', 'std', 'var', 'min', 'max', 'median'):
                is_stat_call = True
                stat_desc = f"np.{node.func.attr}()"
        # Check pd.Series.mean, std, var, min, max, median
        elif isinstance(node.func, ast.Attribute) and node.func.attr in ('mean', 'std', 'var', 'min', 'max', 'median'):
            is_stat_call = True
            stat_desc = f"Series.{node.func.attr}()"
            
        if is_stat_call:
            self.bugs.append({
                "file": self.relative_path,
                "line": node.lineno,
                "type": "Potential NaN Propagation",
                "severity": "Low",
                "description": f"Statistical calculation using {stat_desc} without explicit empty iterable / NaN safety check.",
                "code": self._get_line_content(node.lineno)
            })
            
        # 10. Use of round() without precision parameter
        if isinstance(node.func, ast.Name) and node.func.id == 'round':
            if len(node.args) == 1:
                self.bugs.append({
                    "file": self.relative_path,
                    "line": node.lineno,
                    "type": "Unspecified round() precision",
                    "severity": "Low",
                    "description": "Using round() without decimal places specified. May use default Banker's rounding to integer.",
                    "code": self._get_line_content(node.lineno)
                })
                
        # 11. Use of raw str() on float/statistical vars
        if isinstance(node.func, ast.Name) and node.func.id == 'str' and len(node.args) > 0:
            arg = node.args[0]
            arg_name = ""
            if isinstance(arg, ast.Name):
                arg_name = arg.id
            elif isinstance(arg, ast.Attribute):
                arg_name = arg.attr
            
            unsafe_stat_names = ('sigma', 'std', 'mean', 'cp', 'cpk', 'pp', 'ppk', 'value', 'limit', 'spec', 'nominal')
            if any(name in arg_name.lower() for name in unsafe_stat_names):
                self.bugs.append({
                    "file": self.relative_path,
                    "line": node.lineno,
                    "type": "Unformatted Float String Conversion",
                    "severity": "Low",
                    "description": f"Converting numeric value '{arg_name}' to string using raw str(). Prefer explicit formatting like f'{{val:.4f}}'.",
                    "code": self._get_line_content(node.lineno)
                })
                
        # 12. QComboBox minimum width check (> 180px)
        if isinstance(node.func, ast.Attribute) and node.func.attr in ('setMinimumWidth', 'setFixedWidth'):
            if len(node.args) > 0:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, int) and arg.value > 180:
                    self.bugs.append({
                        "file": self.relative_path,
                        "line": node.lineno,
                        "type": "Violated UI Theme Width Constraint",
                        "severity": "Medium",
                        "description": f"Setting widget width to {arg.value}px which is > 180px constraint. May cause overlap on low resolution.",
                        "code": self._get_line_content(node.lineno)
                    })
        
        self.generic_visit(node)

    def visit_BinOp(self, node):
        # 5. Potential Division by Zero (unsafe denominator)
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            denominator = node.right
            denominator_name = ""
            
            if isinstance(denominator, ast.Name):
                denominator_name = denominator.id
            elif isinstance(denominator, ast.Attribute):
                denominator_name = denominator.attr
            
            unsafe_keywords = ('sigma', 'std', 'count', 'len', 'n', 'denominator', 'size', 'variance', 'val_range')
            if any(kw in denominator_name.lower() for kw in unsafe_keywords):
                self.bugs.append({
                    "file": self.relative_path,
                    "line": node.lineno,
                    "type": "Unsafe Division",
                    "severity": "Low",
                    "description": f"Potential division by zero: denominator '{denominator_name}' may be zero during calculations.",
                    "code": self._get_line_content(node.lineno)
                })
                
        self.generic_visit(node)

    def visit_Assert(self, node):
        # 8. Assert statement in production code
        if self.is_production:
            self.bugs.append({
                "file": self.relative_path,
                "line": node.lineno,
                "type": "Production Assert Statement",
                "severity": "Medium",
                "description": "Assert statement used in production code. Asserts are disabled when Python runs with optimization (-O) flag.",
                "code": self._get_line_content(node.lineno)
            })
        self.generic_visit(node)

    def visit_Raise(self, node):
        # 13. Bare raise outside except handler
        if node.exc is None and self.except_depth == 0:
            self.bugs.append({
                "file": self.relative_path,
                "line": node.lineno,
                "type": "Bare Raise Outside Except",
                "severity": "Critical",
                "description": "Bare 'raise' statement outside of exception handler. Will raise RuntimeError.",
                "code": self._get_line_content(node.lineno)
            })
        self.generic_visit(node)

def scan_directory(directory, is_production=True):
    all_bugs = []
    for root, dirs, files in os.walk(directory):
        if any(p in root for p in ('.venv', '.git', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache')):
            continue
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, directory)
                proj_rel_path = os.path.join(os.path.basename(directory), rel_path)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    tree = ast.parse(content, filename=filepath)
                    scanner = CodebaseBugScanner(filepath, proj_rel_path, is_production)
                    scanner.visit(tree)
                    scanner.scan_comments()
                    all_bugs.extend(scanner.bugs)
                except Exception as e:
                    all_bugs.append({
                        "file": proj_rel_path,
                        "line": 1,
                        "type": "Syntax or Parse Error",
                        "severity": "Critical",
                        "description": f"Failed to parse python file: {str(e)}",
                        "code": ""
                    })
    return all_bugs

if __name__ == "__main__":
    target_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print("Scanning app (production)...")
    bugs = scan_directory(os.path.join(target_dir, "app"), is_production=True)
    
    print("Scanning scripts...")
    bugs.extend(scan_directory(os.path.join(target_dir, "scripts"), is_production=False))
    
    print("Scanning tests...")
    bugs.extend(scan_directory(os.path.join(target_dir, "tests"), is_production=False))
    
    # Filter potential duplicate entries (in case any AST node is visited multiple times or comments overlap)
    unique_bugs = []
    seen = set()
    for bug in bugs:
        key = (bug["file"], bug["line"], bug["type"], bug["description"])
        if key not in seen:
            seen.add(key)
            unique_bugs.append(bug)
            
    print(f"Total potential issues found: {len(unique_bugs)}")
    
    output_path = os.path.join(target_dir, "Outputs", "static_analysis_bugs.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_bugs, f, indent=4, ensure_ascii=False)
        
    print(f"Bugs report saved to: {output_path}")
    
    summary = {}
    for bug in unique_bugs:
        t = bug["type"]
        summary[t] = summary.get(t, 0) + 1
    
    print("\nSummary of issues found:")
    for t, count in summary.items():
        print(f"  - {t}: {count}")
