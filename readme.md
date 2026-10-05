```text
         .8.          8 8888         8 8888  `8.`8888.      ,8'       ,o888888o.    8888 8888
        .888.         8 8888         8 8888   `8.`8888.    ,8'       8888     `88.   88   88 
       :88888.        8 8888         8 8888    `8.`8888.  ,8'     ,8 8888       `8.  88   88
      . `88888.       8 8888         8 8888     `8.`8888.,8'      88 8888            88   88
     .8. `88888.      8 8888         8 8888      `8.`88888'       88 8888            88   88
    .8`8. `88888.     8 8888         8 8888       `8. 8888        88 8888            88   88
   .8' `8. `88888.    8 8888         8 8888        `8 8888        88 8888            88   88
  .8'   `8. `88888.   8 8888         8 8888         8 8888        `8 8888       .8'  88   88
 .888888888. `88888.  8 8888         8 8888         8 8888           8888     ,88'   88   88
.8'       `8. `88888. 8 888888888888 8 888888888888 8 8888            `8888888P'    8888 8888

```

ally-c2 is an open source cross platform c2 framework
that is made to be light weight and customizable

## structure
in ally we have a separate server and cli based client
that connects to the server via ws/wss,
so you can host the server where you want

ally support multi operator mode
so you can work with a team the authentication
credentials are in **server/users.json** 

## installation

```
git clone https://github.com/piadi-su/ally-c2.git

# server
cd server
go build -o ally-server srv.go
./ally-server

# cli-client
cd cliclient
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 ally_cli.py

```

## users.json config
you need to set up **users.json**
before u login with cliclient,
the default credentials are
user=**ally**
passwd=**admin**

make sure to change them

#### get sha256 hash for users.json
```bash
echo -n "password" | sha256sum
```

## https 
to use https you need to have a certificate

#### command for a self signed one
```
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
  -subj "/CN=192.168.1.1" \
  -addext "subjectAltName = IP:192.168.1.1,DNS:localhost"
```
you also need to uncomment certain part of the code

> server/srv.go
```go
	port := ":8080"

	// connection error 
	log.Printf("[*] ally-c2 server (Go) listening on %s...", port)


	// #### uncomment this if u want to use https #####
	certFile := "cert.pem"
	keyFile := "key.pem"

	err := r.RunTLS(port, certFile, keyFile)
	   if err != nil {
	       log.Fatalf("Error: critical server error: %v", err)
	   }



	// #### uncomment this if u want to use http #####

	// err := r.Run(port)
	// if err != nil {
	// 	log.Fatalf("Error: critical server error: %v", err)
	// }

```

> cliclient/ally_cli.py
```python
    
    async def event_listener(event_url):
        try:
            # print(f"\n[DEBUG] connect to channel events: {event_url}")

            # use websockets.connect(event_url,ssl=ssl_context)
            async with websockets.connect(event_url,ssl=ssl_context) as ws:
            # async with websockets.connect(event_url) as ws:

    ...

    async def main(server_url, event_url):
        #use websockets.connect(server_url,ssl=ssl_context) for tls 
        ### UNCOMMENT THIS FOR https
        async with websockets.connect(server_url,ssl=ssl_context) as websocket:
        # async with websockets.connect(server_url) as websocket:

    ...
    #uncomment this if you want to use tls
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    #change this to wss if you are using tls
    server_url = "wss://192.168.1.1:8080/ws/operator"
    events_url= "wss://192.168.1.1:8080/ws/events"
```


## License

Released under the GPLv3 (or later) License.
