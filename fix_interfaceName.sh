#!/bin/bash



# Update references in app.py
echo "Updating references in app.py"
sed -i "s/Interface 1\.py/interface_1.py/g" app.py
sed -i "s/from Interface 1 import/from interface_1 import/g" app.py

# Update references in launch.sh if it exists
if [ -f "launch.sh" ]; then
    echo "Updating references in launch.sh"
    sed -i "s/Interface 1\.py/interface_1.py/g" launch.sh
fi

# Update references in service.sh if it exists
if [ -f "service.sh" ]; then
    echo "Updating references in service.sh"
    sed -i "s/Interface 1\.py/interface_1.py/g" service.sh
fi

echo "Done. Please test your application now."