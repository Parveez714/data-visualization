import uvicorn
import os
import sys

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    os.chdir(current_dir)
    print("Starting AI Data Visualization Backend on http://127.0.0.1:8005 ...")
    uvicorn.run("main:app", host="127.0.0.1", port=8005, reload=True)
