package main

import (
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/coder/websocket"
	"github.com/coder/websocket/wsjson"
)


//single active agent strcut
type AgentSession struct {
	ID          string    `json:"id"`
	LastSeen    time.Time `json:"last_seen"`
	TaskQueue   []string  `json:"task_queue"`   // agent commands queue
	OutputQueue []string  `json:"output_queue"` // latest agent ouput
}

//map of all the agents
var (
	clients = make(map[string]*AgentSession)
	mu      sync.Mutex
)


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

	log.Println("[*] operator connected with success!")

	ctx := c.Request.Context()

	for {
		var msg map[string]interface{}
		err := wsjson.Read(ctx, conn, &msg)
		if err != nil {
			log.Printf("[-] CLI-CLIENT disconnected: %v", err)
			break
		}

		log.Printf("[Command recived] -> Action: %v, Arg: %v", msg["action"], msg["data"])

		response := map[string]string{
			"status": "success",
			"output": "Command recived in elaboration fase",
		}
		err = wsjson.Write(ctx, conn, response)
		if err != nil {
			log.Printf("[-] error sending msg back: %v", err)
			break
		}
	}
}

func main() {
	r := gin.Default()

	port := ":8080"

	//operator enpoint 
	//cli endpoint with ws
	r.GET("/ws/operator", handleOperator)


	//agent endpoints--------
	//direct shell access with ws
	r.GET("/api/ws/dirsh", handleOperator)
	
	//task poll ep
	r.GET("/api/agent/poll", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status": "no_tasks",
			"command": "",
		})
	})

	//command output ep
	r.POST("/api/agent/output", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status": "received",
		})
	})

	log.Printf("[*] ally-c2 listening on %s...", port)
	
	err := r.Run(port)
	if err != nil {
		log.Fatalf("Error: critical server error: %v", err)
	}
}
