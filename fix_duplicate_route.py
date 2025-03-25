import re

# Read the app.py file
with open('app.py', 'r') as f:
    content = f.read()

# Find and remove duplicate route definitions
routes_to_fix = [
    '/hardware_status',
    '/sensor_data',
    '/test_hardware_fixed',
    '/websocket_test',
    '/hardware_test_page',
    '/debug/sensor'
]

# Find where the main block starts
main_block_match = re.search(r'if __name__ == [\'"]__main__[\'"]:.*$', content, re.DOTALL)
if not main_block_match:
    print("Could not find main block in app.py")
    exit(1)

main_block_start = main_block_match.start()

# For each route, find all occurrences after the first one and remove them
for route in routes_to_fix:
    pattern = r'@app\.route\([\'"]{}[\'"].*?\ndef .*?\):.*?(?=@app\.route|if __name__|$)'.format(route)
    matches = list(re.finditer(pattern, content, re.DOTALL))
    
    if len(matches) > 1:
        print(f"Found {len(matches)} occurrences of route {route}")
        
        # Keep the first occurrence before the main block
        first_match = None
        for match in matches:
            if match.start() < main_block_start:
                first_match = match
                break
        
        if first_match:
            # Remove all other occurrences
            for match in matches:
                if match != first_match:
                    start, end = match.span()
                    content = content[:start] + content[end:]
            print(f"Kept the first occurrence of {route} and removed {len(matches)-1} duplicates")
        else:
            print(f"No occurrences of {route} found before main block")
    else:
        print(f"Found only 1 occurrence of route {route} or none at all")

# Write the cleaned content back to app.py
with open('app.py', 'w') as f:
    f.write(content)

print("Removed duplicate route definitions in app.py")