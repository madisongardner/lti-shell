#!/bin/bash
echo "Running tests..."

# Check if hello.sh exists
if [ -f /workspace/hello.sh ]; then
    OUTPUT=$(bash /workspace/hello.sh 2>&1)
    if echo "$OUTPUT" | grep -qi "hello"; then
        echo "PASS: hello.sh prints a greeting"
        echo "SCORE = 100"
    else
        echo "FAIL: hello.sh did not print a greeting"
        echo "SCORE = 50"
    fi
else
    echo "FAIL: hello.sh not found"
    echo "SCORE = 0"
fi
