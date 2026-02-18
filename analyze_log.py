
try:
    with open('error.log', 'r', encoding='utf-16') as f:
        content = f.read()
except UnicodeError:
    try:
        with open('error.log', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Could not read file: {e}")
        exit(1)

lines = content.splitlines()
found_exception = False
for i, line in enumerate(lines):
    if "Exception Value" in line or "Exception Location" in line:
        print(line.strip())
        # Print next few lines
        for j in range(1, 5):
            if i + j < len(lines):
                print(lines[i+j].strip())
        found_exception = True

if not found_exception:
    print("Could not find 'Exception Value' in log. Dumping first 100 lines...")
    for line in lines[:100]:
        print(line)
