#!/usr/bin/env python3
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    print(f"INFO: Binding to port {port} (from environment PORT={os.getenv('PORT')})")
    uvicorn.run("main:app", host="0.0.0.0", port=port)
