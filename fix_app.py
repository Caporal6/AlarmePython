import re

# Read the app.py file
with open('app.py', 'r') as file:
    content = file.read()

# Find the problematic route definitions
websocket_route = re.search(r'@app\.route\(\'/websocket_test\'\)\s*def websocket_test\(\):[^}]*?return render_template\(\'test.html\'\)', content, re.DOTALL)
hardware_route = re.search(r'@app\.route\(\'/hardware_test_page\'\)\s*def hardware_test_page\(\):[^}]*?return render_template\(\'hardware_test.html\'\)', content, re.DOTALL)

if websocket_route and hardware_route:
    # Remove these routes from their current locations
    content = content.replace(websocket_route.group(0), '')
    content = content.replace(hardware_route.group(0), '')
    
    # Find a good place to put them (before the if __name__ block)
    main_block = re.search(r'if __name__ == \'__main__\':', content)
    if main_block:
        insert_point = main_block.start()
        
        # Add the routes at the insert point
        content = (content[:insert_point] + 
                  "\n@app.route('/websocket_test')\n" +
                  "def websocket_test():\n" +
                  '    """Test page for WebSocket connections"""\n' +
                  "    return render_template('test.html')\n\n" +
                  "@app.route('/hardware_test_page')\n" +
                  "def hardware_test_page():\n" +
                  '    """Dedicated page for testing hardware components"""\n' +
                  "    return render_template('hardware_test.html')\n\n" +
                  content[insert_point:])
        
        # Write the fixed content back
        with open('app.py', 'w') as file:
            file.write(content)
        
        print("Routes fixed successfully.")
    else:
        print("Could not find if __name__ == '__main__' block.")
else:
    print("Could not find the route definitions.")