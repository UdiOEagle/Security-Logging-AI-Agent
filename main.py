"""
Perplexity PDF reviewer → APPENDS results to single master JSON file.
Requires: pip install PyPDF2 openai python-dotenv
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from PyPDF2 import PdfReader
from openai import OpenAI
from dotenv import load_dotenv
import base64


load_dotenv()


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract all text from PDF."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text.strip()


def parse_results(content: str) -> List[Dict]:
    """
    Parse AI response into structured events.
    """
    lines = content.strip().split("\n")
    results = []
    
    if lines and lines[0].strip() == "***N/A***":
        results.append({
            "status": "no_events",
            "explanation": "\n".join(line.strip() for line in lines[1:]).strip()
        })
    else:
        blocks = content.split("Specification section:")
        for block in blocks[1:]:
            lines = block.strip().split("\n")
            event = {}
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    event[key.strip()] = value.strip().strip("'")
            if event:
                results.append(event)
    
    return results


def append_to_master_json(results: List[Dict], pdf_filename: str, master_file: Path):
    """Append new results to master JSON file."""
    timestamp = datetime.now().isoformat()
    new_entry = {
        "processed_at": timestamp,
        "pdf_file": pdf_filename,
        "num_events": len(results),
        "events": results
    }
    
    # Load existing or create new
    if master_file.exists():
        with open(master_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"pdf_analyses": []}
    
    data["pdf_analyses"].append(new_entry)
    
    # Save back (atomic write)
    with open(master_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Appended to master file: {master_file}")
    print(f"📊 Total analyses: {len(data['pdf_analyses'])}")
    
def check_file_already_proccessed(pdf_filename: str, master_file: Path) -> bool:
    # Load file or return False:
    if master_file.exists():
        with open(master_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            #check if any pdf_file entry in the JSON file matched the reciever master_file Path:
            for file in data["pdf_analyses"]:
                if pdf_filename in file["pdf_file"]:
                    return True    
    return False
    

def main():
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("Set PERPLEXITY_API_KEY in .env file")
    
    master_json = Path("autosar_security_events.json")  # Single master file    
    if not os.path.exists(master_json):
        while True:
            x = input("⚠️ master_json file not found. Program will run through all files. Do you want to continue ? (y/n)\n")
            if(x == 'y' or x=='Y'):
                break
            if(x=='n' or x=='N'):
                print("❌ Exiting...")
                return
            
    
    folder_path = r"./Autosar_Standards/R25-11/CP"
        
    #crawl through every pdf file name insider foolder_path
    for name in os.listdir(folder_path):
        full_path = os.path.join(folder_path, name)
        if os.path.isfile(full_path):  # optional: only files
            if ".pdf" in name: #only PDFs
                print(f"⚙️ Processing {full_path}...")
    
                pdf_path = Path(full_path)
                
                #check if file was already proccessed 
                if not check_file_already_proccessed(master_file=master_json, pdf_filename=pdf_path.name):
                    with open(pdf_path, "rb") as f:
                        print("📄 Converting PDF to Base64 format...")
                        
                        pdf_b64 = base64.b64encode(f.read()).decode("utf-8")
                        
                        client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
                        
                        system_prompt = f"""You are a world class security engineer reviewing {pdf_path} 
                        (part of the latest AUTOSAR specification). Your job is to review the attached pdf file analyze it and identify and suggest new relevant security event logs.
                        ONLY SUGGEST HIGHLY RELEVANT NEW SECURITY EVENT LOGS. 
                        (not similar/identical to existing ones).
                        IF YOU DONT THINK YOU HAVE ANY NEW HIGHLY RELEVANT SECURITY EVENT LOGS, THEN DONT SUGGEST THEM.

                        FORMAT (if events exist):
                        Specification section: 'Filename'
                        System event: 'name of suggested new event'
                        Suggested log: 'context variable names to be added to the log context'
                        Rationale: 'Explain the reasoning behind choosing this new event'

                        FORMAT (if no new events):
                        ***N/A***
                        (explanation as of why not)"""

                        print("🤖 Analyzing with sonar model...")
                        response = client.chat.completions.create(
                            model="sonar",  # Cheapest
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": [ 
                                    {"type": "text", "text": "Read the attached BASE64 PDF file and extract the findings according to the system instructions."},
                                    {"type": "file_url", "file_url": {"url": pdf_b64}, "file_name": pdf_path.name},]}],
                            temperature=0.1,
                            max_tokens=2048,
                        )
                        
                        content = response.choices[0].message.content
                        print("\n📋 Response preview:")
                        print(content[:100] + "..." if len(content) > 100 else content)
                        
                        # Parse & append to master JSON
                        results = parse_results(content)
                        append_to_master_json(results, pdf_path.name, master_json)
                        
                        print(f"\n💾 Master file updated:")

                #file has already been proccessed
                else:
                    print("⚠️  File has already been processed. Skipping to next file in line.")

if __name__ == "__main__":
    main()
