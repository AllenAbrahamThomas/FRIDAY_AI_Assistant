import urllib.request
import zipfile
import io
import os
import sys

def setup_ollama():
    url = "https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.zip"
    dest_dir = os.path.abspath(".venv/Scripts")

    if not os.path.exists(dest_dir):
        print(f"Error: Virtual environment script folder not found at '{dest_dir}'.")
        print("Please make sure you have created the .venv first by running: python -m venv .venv")
        sys.exit(1)

    print("==========================================================")
    print("FRIDAY AI - Standalone Ollama Setup Subsystem")
    print("==========================================================")
    print(f"Target Download URL: {url}")
    print(f"Destination Path   : {dest_dir}")
    print("----------------------------------------------------------")
    print("Connecting to GitHub to download portable Ollama...")

    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            zip_data = response.read()
        
        print("Download complete. Extracting files...")
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_ref:
            # Extract all files into .venv/Scripts/ so they are on the activated PATH
            zip_ref.extractall(dest_dir)
            
        print("----------------------------------------------------------")
        print("SUCCESS: Standalone Ollama successfully installed inside .venv!")
        print("To verify, activate your environment and run:")
        print("  1. ollama serve (Starts the background server)")
        print("  2. ollama pull llama3.2 (Pulls the target model)")
        print("==========================================================")
    except Exception as e:
        print(f"Error setting up Ollama inside environment: {str(e)}")
        print("Please check your internet connection or install Ollama globally from https://ollama.com/")

if __name__ == "__main__":
    setup_ollama()
