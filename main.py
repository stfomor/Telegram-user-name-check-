import os
import sys
import time
import asyncio
import aiohttp
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

AVAILABLE = 0
TAKEN = 0

def banner(config):
    os.system('cls' if os.name == 'nt' else 'clear')
    banner_text = r"""
   ______           __                     ____             ___
  / ____/___ ______/ /_  ____ _____ ____  / __ )____ _____ <  /
 / / __/ __ `/ ___/ __ \/ __ `/ __ `/ _ \/ __  / __ `/ __ `/ / 
/ /_/ / /_/ / /  / /_/ / /_/ / /_/ /  __/ /_/ / /_/ / /_/ / /  
\____/\__,_/_/  /_.___/\__,_/\__, /\___/_____/\__,_/\__, /_/   
                            /____/                 /____/

   ____  __  ___   ___    ____     _________    ____  __  ___
  / __ \/  |/  /  /   |  / __ \   / ____/   |  / __ \/ / / / |
 / / / / /|_/ /  / /| | / /_/ /  / /_  / /| | / /_/ / / / /  |
/ /_/ / /  / /  / ___ |/ _, _/  / __/ / ___ |/ _, _/ /_/ / /| |
\____/_/  /_/  /_/  |_/_/ |_|  /_/   /_/  |_/_/ |_|\____/_/ |_|

                  Facebook:stfomorfaruk
"""
    print(Fore.CYAN + banner_text + Style.RESET_ALL if config.get("color") == "1" else banner_text)

def timestamp():
    return datetime.now().strftime("%d-%m-%Y")

def load_config(path="config.txt"):
    default = {"color": "1", "logs": "1", "results": "1", "concurrency": "50"}
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            for k, v in default.items():
                f.write(f"{k} {v}\n")
        return default
    
    config = default.copy()
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and " " in line:
                k, v = line.split(None, 1)
                config[k.strip()] = v.strip()
    return config

def load_usernames(file, config):
    if not os.path.exists(file):
        with open(file, 'w', encoding='utf-8'): pass
        text = f"[!] '{file}' created. Add usernames inside."
        print(Fore.YELLOW + text if config.get("color") == "1" else text) 
        return []
    with open(file, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def save_result(text, folder="results"):
    os.makedirs(folder, exist_ok=True)
    with open(f"{folder}/Valid-{timestamp()}.txt", 'a', encoding='utf-8') as f:
        f.write(text + '\n')

def save_all_checked(text, folder="results"):
    os.makedirs(folder, exist_ok=True)
    with open(f"{folder}/All-Checked-{timestamp()}.txt", 'a', encoding='utf-8') as f:
        f.write(text + '\n')

def save_log(text, folder="logs"):
    os.makedirs(folder, exist_ok=True)
    with open(f"{folder}/Log-{timestamp()}.txt", 'a', encoding='utf-8') as f:
        f.write(text + '\n')

# অসিনক্রোনাস ইউজারনেম চেকার
async def check_username(session, username, config, semaphore):
    global AVAILABLE, TAKEN
    
    url = f"https://fragment.com/username/{username.lower()}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    async with semaphore: # একসাথে কয়টি রিকোয়েস্ট যাবে তা নিয়ন্ত্রণ করবে
        try:
            async with session.get(url, headers=headers, allow_redirects=False, timeout=6) as r:
                if r.status == 302:
                    text = f"[+] {username} - available"
                    print(Fore.GREEN + text if config.get("color") == "1" else text)
                    
                    if config.get("results") == "1": 
                        save_result(username)
                    save_all_checked(f"{username} - Available")
                    AVAILABLE += 1
                else:
                    text = f"[-] {username} - taken"
                    print(Fore.RED + text if config.get("color") == "1" else text)
                    
                    save_all_checked(f"{username} - Taken")
                    TAKEN += 1
                    
                if config.get("logs") == "1":
                    save_log(text)
                    
        except Exception as e:
            err = f"[!] {username} - error: {e}"
            print(Fore.MAGENTA + err if config.get("color") == "1" else err)
            save_all_checked(f"{username} - Error ({e})")
            if config.get("logs") == "1":
                save_log(err)

async def async_main():
    global AVAILABLE, TAKEN
    config = load_config()
    banner(config)
    usernames = load_usernames("usernames.txt", config)
    
    if not usernames:
        name = input("[?] Enter one username to check:\n[>] ").strip()
        if name:
            # একক ইউজার চেকের জন্য সাময়িক সেশন
            semaphore = asyncio.Semaphore(1)
            async with aiohttp.ClientSession() as session:
                await check_username(session, name, config, semaphore)
        else:
            print(Fore.MAGENTA + "[~] Nothing entered." if config.get("color") == "1" else "[~] Nothing entered.")
        return

    print(Fore.WHITE + f"[#] Starting Fast Check.. (found {len(usernames)} usernames)\n" if config.get("color") == "1" else f"[#] Starting Fast Check.. (found {len(usernames)} usernames)\n")
    
    # একসাথে কতগুলো রিকোয়েস্ট সার্ভারে হিট করবে (Concurrency)
    # ১০০০+ স্পিড পেতে ৫০ থেকে ১০০ এর মধ্যে রাখুন
    try:
        concurrency_limit = int(config.get("concurrency", "50"))
    except ValueError:
        concurrency_limit = 50
        
    semaphore = asyncio.Semaphore(concurrency_limit)
    
    # অসিনক্রোনাস সেশন তৈরি
    async with aiohttp.ClientSession() as session:
        tasks = []
        for username in usernames:
            # সব টাস্ক একসাথে ব্যাকগ্রাউন্ডে রেডি করা হচ্ছে
            tasks.append(check_username(session, username, config, semaphore))
            
        # সব টাস্ক একসাথে রান করানো হচ্ছে
        await asyncio.gather(*tasks)
        
    # শেষ ফলাফল প্রিন্ট
    text = "\n[#] Finished.\n[#] Results: "
    text2 = f"{AVAILABLE}"
    text3 = " | "
    text4 = f"{TAKEN}"
    text5 = f" (saved to Valid-{timestamp()}.txt and All-Checked-{timestamp()}.txt)"
    
    if config.get("results") == "1" and AVAILABLE > 0:
        print(Fore.WHITE + text + Fore.GREEN + text2 + Fore.WHITE + text3 + Fore.RED + text4 + Fore.CYAN + text5 if config.get("color") == "1" else text + text2 + text3 + text4 + text5)
    else:
        print(Fore.WHITE + text + Fore.GREEN + text2 + Fore.WHITE + text3 + Fore.RED + text4 if config.get("color") == "1" else text + text2 + text3 + text4)

if __name__ == "__main__":
    # অসিনক্রোনাস লুপ স্টার্ট করা
    asyncio.run(async_main())
