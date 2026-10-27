def verify_all_code_tags():
    with open('docs/capitulo 7/capitulo_7_implementacion.tex', 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.splitlines()
    in_listing = False
    
    for i, line in enumerate(lines, 1):
        if r'\begin{lstlisting}' in line:
            in_listing = True
            continue
        if r'\end{lstlisting}' in line:
            in_listing = False
            continue
        if in_listing:
            continue
            
        idx = 0
        while True:
            pos = line.find(r'\code{', idx)
            if pos == -1:
                break
            brace_count = 0
            closed = False
            for j in range(pos + 5, len(line)):
                if line[j] == '%' and (j == 0 or line[j-1] != '\\'):
                    break
                if line[j] == '{':
                    brace_count += 1
                elif line[j] == '}':
                    if brace_count == 0:
                        closed = True
                        idx = j + 1
                        break
                    else:
                        brace_count -= 1
            if not closed:
                print(f"Line {i} has unclosed \\code: {line}")
                idx = pos + 6

if __name__ == "__main__":
    verify_all_code_tags()
