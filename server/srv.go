package main

import (
	"log"
	"net/http"

	"github.com/coder/websocket"
	"github.com/coder/websocket/wsjson"
)

func handleOperator(w http.ResponseWriter, r *http.Request) {
	// Accetta la connessione WebSocket (per i lab disabilitiamo il controllo rigido dell'Origin)
	opts := &websocket.AcceptOptions{
		InsecureSkipVerify: true,
	}
	
	conn, err := websocket.Accept(w, r, opts)
	if err != nil {
		log.Printf("Errore durante l'handshake WebSocket: %v", err)
		return
	}
	defer conn.Close(websocket.StatusNormalClosure, "Chiusura sessione")

	log.Println("[+] CLI Operatore connessa con successo!")

	ctx := r.Context()

	for {
		// Legge un messaggio JSON inviato dalla CLI
		var msg map[string]interface{}
		err := wsjson.Read(ctx, conn, &msg)
		if err != nil {
			log.Printf("[-] CLI disconnessa o errore di lettura: %v", err)
			break
		}

		log.Printf("[Comando ricevuto] -> Azione: %v, Arg: %v", msg["action"], msg["data"])

		// Esempio di risposta immediata indietro alla CLI
		response := map[string]string{
			"status": "success",
			"output": "Comando ricevuto dal server e in elaborazione...",
		}
		err = wsjson.Write(ctx, conn, response)
		if err != nil {
			log.Printf("[-] Errore nell'invio della risposta: %v", err)
			break
		}
	}
}

func main() {
	http.HandleFunc("/ws/operator", handleOperator)
	
	log.Println("[*] Server C&C in ascolto sulla porta 8080...")
	err := http.ListenAndServe(":8080", nil)
	if err != nil {
		log.Fatalf("Errore critico del server: %v", err)
	}
}
