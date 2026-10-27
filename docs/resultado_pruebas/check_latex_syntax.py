def check_latex_syntax():
    with open('docs/capitulo 7/capitulo_7_implementacion.tex', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_listing = False
    issues = []
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if r'\begin{lstlisting}' in s:
            in_listing = True
            continue
        if r'\end{lstlisting}' in s:
            in_listing = False
            continue
        if in_listing:
            continue
            
        # Outside listings, look for unescaped % that is not on a line by itself
        idx = 0
        while True:
            pos = line.find('%', idx)
            if pos == -1:
                break
            if pos == 0:
                # whole line is comment, normal in latex
                break
            if line[pos-1] != '\\':
                # unescaped % with text before it
                before = line[:pos]
                # check if there is an unclosed brace before %
                open_b = before.count('{')
                close_b = before.count('}')
                if open_b > close_b:
                    issues.append((i, f"UNCLOSED BRACE before %: {line.strip()}"))
                else:
                    # check if it looks like a code or text
                    if any(w in line[pos:pos+10] for w in ['s', 'd', 'f', '(', ')']):
                        issues.append((i, f"Possible unescaped % parameter: {line.strip()}"))
                break
            idx = pos + 1
            
    print(f"Total issues found: {len(issues)}")
    for line_num, desc in issues:
        print(f"Line {line_num}: {desc}")

if __name__ == "__main__":
    check_latex_syntax()
